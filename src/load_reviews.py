import sqlite3
import pandas as pd
import requests
import time
from tqdm import tqdm
import os
import logging
from transformers import pipeline

# Configuration
DATABASE_NAME = "anime.db"
NUM_TOP_ANIME = 500 # Adjust as needed
MAX_REVIEWS_PER_ANIME = 20 
DELAY_BETWEEN_REQUESTS = 1 # Seconds to wait between Jikan API calls
SENTIMENT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"

# Set up logging (optional, but helpful for debugging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize sentiment analysis pipeline
try:
    sentiment_pipeline = pipeline(
        "sentiment-analysis", 
        model=SENTIMENT_MODEL, 
        tokenizer=SENTIMENT_MODEL
    )
except Exception as e:
    logging.error(f"Failed to load sentiment pipeline: {e}")
    sentiment_pipeline = None

# --- UPDATED: Schema Management Function ---
def setup_reviews_table(conn):
    """
    Ensures the 'reviews' table exists with all necessary columns (including the new sentiment_label).
    If the table exists but is missing required columns, it adds them.
    """
    cursor = conn.cursor()
    
    # 1. Check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        logging.info("Creating 'reviews' table with all required columns.")
        # Create the table with all required columns, including the new 'sentiment_label'
        cursor.execute("""
            CREATE TABLE reviews (
                review_id INTEGER,
                review_text TEXT,
                sentiment_ REAL,
                sentiment_label TEXT,
                anime_mal_id INTEGER,
                PRIMARY KEY (review_id, anime_mal_id) -- Composite key to prevent duplicates
            )
        """)
        conn.commit()
        return

    # 2. Check for required columns if table exists
    cursor.execute("PRAGMA table_info(reviews)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Check and add anime_mal_id
    if 'anime_mal_id' not in columns:
        logging.info("Adding missing 'anime_mal_id' column to 'reviews' table.")
        cursor.execute("ALTER TABLE reviews ADD COLUMN anime_mal_id INTEGER")
        conn.commit()
    
    # Check and add sentiment_score
    if 'sentiment_' not in columns:
        logging.info("Adding missing 'sentiment_' column to 'reviews' table.")
        cursor.execute("ALTER TABLE reviews ADD COLUMN sentiment_ REAL")
        conn.commit()

    # Check and add NEW sentiment_label
    if 'sentiment_label' not in columns:
        logging.info("Adding new 'sentiment_label' column to 'reviews' table.")
        cursor.execute("ALTER TABLE reviews ADD COLUMN sentiment_label TEXT")
        conn.commit()

# --- Utility Functions ---

def analyze_sentiment(text):
    """Analyze sentiment and return a score (-1 to 1) and label (POSITIVE/NEGATIVE)"""
    if not sentiment_pipeline:
        return 0.0, "UNKNOWN"
    
    try:
        # The pipeline returns [{'label': 'POSITIVE'/'NEGATIVE', 'score': 0.999}]
        # Limit text length for BERT model token limit (512 tokens is usually safe)
        result = sentiment_pipeline(text[:512])[0] 
        score = result['score']
        label = result['label']
        
        # Convert score to a spectrum: 
        # POSITIVE -> 0 to 1.0 (maintains score)
        # NEGATIVE -> -1.0 to 0 (score is negated)
        if label == 'NEGATIVE':
            return -score, label
        else:
            return score, label
            
    except Exception as e:
        logging.warning(f"Sentiment analysis failed for review: {e}")
        return 0.0, "ERROR"

def fetch_reviews_for_anime(mal_id):
    """Fetches reviews for a given anime ID from the Jikan API."""
    reviews_data = []
    page = 1
    
    # Jikan API endpoint for reviews
    url = f"https://api.jikan.moe/v4/anime/{mal_id}/reviews"
    
    while len(reviews_data) < MAX_REVIEWS_PER_ANIME:
        try:
            response = requests.get(f"{url}?page={page}")
            if response.status_code == 429:
                logging.warning("Rate limit hit. Waiting 60 seconds...")
                time.sleep(60)
                continue
            
            response.raise_for_status()
            data = response.json()
            
            new_reviews = data.get('data', [])
            if not new_reviews:
                break # No more reviews

            for review in new_reviews:
                review_text = review.get('review')
                if review_text:
                    # Sanitize text: remove [Written by MAL user] and similar tags
                    clean_text = review_text.split('[Written by MAL user]')[0].strip()
                    
                    # Sentiment analysis - returns score and label
                    sentiment_score, sentiment_label = analyze_sentiment(clean_text)
                    
                    reviews_data.append({
                        'review_id': review.get('mal_id'), # Use MAL review ID
                        'review_text': clean_text,
                        'sentiment_': sentiment_score,
                        'sentiment_label': sentiment_label, # New column for label
                        'anime_mal_id': mal_id # Attach the anime ID
                    })
                
                if len(reviews_data) >= MAX_REVIEWS_PER_ANIME:
                    break
            
            if data.get('pagination', {}).get('has_next_page') and len(reviews_data) < MAX_REVIEWS_PER_ANIME:
                page += 1
                time.sleep(DELAY_BETWEEN_REQUESTS)
            else:
                break
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logging.warning(f"No reviews found for mal_id={mal_id} (404 error).")
            else:
                logging.error(f"HTTP Error fetching reviews for mal_id={mal_id}: {e}")
            break
        except Exception as e:
            logging.error(f"Unexpected error for mal_id={mal_id}: {e}")
            break

    return reviews_data

def save_reviews_to_db(conn, reviews_df):
    """Saves the DataFrame of reviews to the SQLite database."""
    if reviews_df.empty:
        return
    
    # Since we are using a composite PRIMARY KEY (review_id, anime_mal_id), 
    # using 'append' is safe, but we should explicitly prevent inserting the same review 
    # for the same anime if it already exists to avoid errors, although drop_duplicates 
    # handles this mostly. We rely on sqlite's behavior with primary keys here.
    
    reviews_df.to_sql('reviews', conn, if_exists='append', index=False)
    
def main():
    conn = sqlite3.connect(DATABASE_NAME)
    
    # 1. Initialize/Fix the 'reviews' table schema
    setup_reviews_table(conn)

    # 2. Get the top N anime IDs from the 'anime' table
    try:
        anime_df = pd.read_sql_query(f"SELECT mal_id, title FROM anime ORDER BY score DESC LIMIT {NUM_TOP_ANIME}", conn)
    except Exception:
        logging.error("Could not read from 'anime' table. Please run load_data.py first.")
        conn.close()
        return

    logging.info(f"Fetching reviews for top {len(anime_df)} anime... ({len(anime_df)} available)")

    all_reviews = []
    
    # 3. Fetch reviews for each anime
    for index, row in tqdm(anime_df.iterrows(), total=anime_df.shape[0], desc="Anime"):
        reviews = fetch_reviews_for_anime(row['mal_id'])
        all_reviews.extend(reviews)
        time.sleep(DELAY_BETWEEN_REQUESTS) # Respect API limits

    # 4. Save all collected reviews
    if all_reviews:
        all_reviews_df = pd.DataFrame(all_reviews)
        
        # Remove duplicates based on the review ID, keeping the first occurrence (which links it to an anime)
        # Note: We rely on the DB's PRIMARY KEY constraint for true uniqueness across runs.
        all_reviews_df = all_reviews_df.drop_duplicates(subset=['review_id', 'anime_mal_id'], keep='first')
        
        save_reviews_to_db(conn, all_reviews_df)
        logging.info(f"Successfully loaded {len(all_reviews_df)} reviews in total.")
    else:
        logging.info("No reviews were fetched or processed.")

    conn.close()

if __name__ == "__main__":
    main()
