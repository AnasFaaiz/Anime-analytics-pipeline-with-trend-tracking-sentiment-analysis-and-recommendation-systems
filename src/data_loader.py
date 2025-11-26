import sqlite3
import pandas as pd
import requests
import time
from tqdm import tqdm
import logging
from transformers import pipeline

# Configuration
DATABASE_NAME = "anime.db"
NUM_TOP_ANIME = 500 
MAX_REVIEWS_PER_ANIME = 20
JIKAN_API_URL = "https://api.jikan.moe/v4"
DELAY_BETWEEN_REQUESTS = 1.5
SENTIMENT_MODEL = "distilbert-base-uncased-finetined-sst-2-english"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Sentiment Model Setup ---
try:
    sentiment_pipeline = pipeline(
        "sentiment-analysis", 
        model=SENTIMENT_MODEL, 
        tokenizer=SENTIMENT_MODEL
    )
except Exception as e:
    logging.error(f"Failed to load sentiment pipeline: {e}. Sentiment analysis will be skipped.")
    sentiment_pipeline = None

# --- Database Schema Functions (Adopted from your provided schema) ---

def setup_database_schema(conn):
    """
    Creates or ensures the 'anime' and 'reviews' tables have the correct schema,
    including all required columns (original score, reviewer name) and FOREIGN KEY.
    """
    cursor = conn.cursor()
    
    # NOTE: We use IF NOT EXISTS here to avoid deleting existing data on subsequent runs.
    # If you want to force a fresh start (like your original `create_database`),
    # uncomment the DROP TABLE commands below.
    # cursor.execute("DROP TABLE IF EXISTS reviews")
    # cursor.execute("DROP TABLE IF EXISTS anime")
    
    # 1. ANIME TABLE
    logging.info("Ensuring 'anime' table schema is correct.")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS anime (
        mal_id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        score REAL,
        episodes INTEGER,
        status TEXT,
        genres TEXT,
        studio TEXT,
        aired TEXT,
        image_url TEXT,
        synopsis TEXT,
        popularity INTEGER,
        members INTEGER
    );
    """)
    
    # 2. REVIEWS TABLE
    logging.info("Ensuring 'reviews' table schema is correct.")
    # We use review_id from Jikan as the PRIMARY KEY combined with anime_mal_id
    # to enforce uniqueness and allow for easy lookups/updates.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        review_id INTEGER,
        anime_mal_id INTEGER,
        review_text TEXT NOT NULL,
        reviewer_name TEXT,
        date TEXT,
        score INTEGER,                 -- Original MAL score (1-10)
        sentiment_label TEXT,          -- POSITIVE/NEGATIVE label
        sentiment_ REAL,               -- Calculated sentiment score (-1 to 1)
        
        PRIMARY KEY (review_id, anime_mal_id),
        FOREIGN KEY (anime_mal_id) REFERENCES anime(mal_id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_anime ON reviews(anime_mal_id);")

    # Add columns if they were missing (Robustness check - useful if the table existed before)
    def add_missing_column(table, column, definition):
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        if column not in columns:
            logging.info(f"Adding missing column '{column}' to '{table}' table.")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    # Ensure all review columns are present
    add_missing_column('reviews', 'reviewer_name', 'TEXT')
    add_missing_column('reviews', 'date', 'TEXT')
    add_missing_column('reviews', 'score', 'INTEGER')
    add_missing_column('reviews', 'sentiment_label', 'TEXT')
    add_missing_column('reviews', 'sentiment_', 'REAL')
    add_missing_column('reviews', 'anime_mal_id', 'INTEGER')
    
    conn.commit()


# --- Anime Data Fetching and Cleaning (No changes needed here) ---

def fetch_and_clean_anime(num_anime):
    """Fetches the top N anime from Jikan API, handles pagination, and cleans data."""
    all_anime_data = []
    
    pages_to_fetch = (num_anime + 24) // 25 
    
    logging.info(f"Fetching {num_anime} top anime across {pages_to_fetch} pages...")

    for page in tqdm(range(1, pages_to_fetch + 1), desc="Fetching Anime Pages"):
        try:
            url = f"{JIKAN_API_URL}/top/anime?page={page}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data:
                for anime in data['data']:
                    if len(all_anime_data) >= num_anime:
                        break
                        
                    genres = ", ".join([g['name'] for g in anime.get('genres', [])])
                    studios = ", ".join([s['name'] for s in anime.get('studios', [])])
                    
                    prepared_data = (
                        anime.get('mal_id'),
                        anime.get('title'),
                        anime.get('score', 0),
                        anime.get('episodes', 0),
                        anime.get('status', 'Unknown'),
                        genres,
                        studios,
                        anime.get('aired', {}).get('string', 'Unknown'),
                        anime.get('images', {}).get('jpg', {}).get('image_url', None),
                        anime.get('synopsis', 'No synopsis available.'),
                        anime.get('popularity', 0),
                        anime.get('members', 0)
                    )
                    all_anime_data.append(prepared_data)
                
            time.sleep(DELAY_BETWEEN_REQUESTS)

        except Exception as e:
            logging.error(f"Error fetching anime page {page}: {e}")
            time.sleep(5)

    return all_anime_data


def load_anime_to_db(conn, data):
    """Inserts anime metadata into the database."""
    cursor = conn.cursor()
    logging.info(f"Inserting {len(data)} anime titles into DB...")
    
    # Use INSERT OR REPLACE to update existing anime if their score/status changes
    cursor.executemany("""
    INSERT OR REPLACE INTO anime (mal_id, title, score, episodes, status, genres, studio, aired, image_url, synopsis, popularity, members)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    
    conn.commit()
    return cursor.rowcount

# --- Review Data Fetching and Analysis (Updated to capture original score/name/date) ---

def analyze_sentiment(text):
    """Analyze sentiment and return a score (-1 to 1) and label (POSITIVE/NEGATIVE)"""
    if not sentiment_pipeline:
        return 0.0, "SKIPPED"
    
    try:
        result = sentiment_pipeline(text[:512])[0] 
        score = result['score']
        label = result['label']
        
        if label == 'NEGATIVE':
            return -score, label
        else:
            return score, label
            
    except Exception as e:
        logging.warning(f"Sentiment analysis failed: {e}")
        return 0.0, "ERROR"

def fetch_and_load_reviews(conn, anime_list):
    """Loops through anime, fetches reviews, analyzes sentiment, and saves to DB."""
    all_reviews_data = []
    
    anime_map = {anime[0]: anime[1] for anime in anime_list} 
    
    logging.info("\n--- Starting Review Fetching and Sentiment Analysis ---")
    
    for mal_id, title in tqdm(anime_map.items(), desc="Anime Reviews"):
        review_url = f"{JIKAN_API_URL}/anime/{mal_id}/reviews"
        reviews_data = []
        page = 1
        
        while len(reviews_data) < MAX_REVIEWS_PER_ANIME:
            try:
                response = requests.get(f"{review_url}?page={page}")
                if response.status_code == 429:
                    logging.warning(f"Rate limit hit. Waiting 60 seconds before continuing with {title}...")
                    time.sleep(60)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                new_reviews = data.get('data', [])
                if not new_reviews:
                    break

                for review in new_reviews:
                    review_text = review.get('review')
                    if review_text:
                        clean_text = review_text.split('[Written by MAL user]')[0].strip()
                        
                        # Sentiment analysis
                        sentiment_score, sentiment_label = analyze_sentiment(clean_text)
                        
                        reviews_data.append({
                            'review_id': review.get('mal_id'),
                            'anime_mal_id': mal_id, 
                            'review_text': clean_text,
                            'reviewer_name': review.get('user', {}).get('username', 'Anonymous'), # CAPTURED
                            'date': review.get('date', ''),                                      # CAPTURED
                            'score': review.get('score'),                                        # CAPTURED (Original MAL score)
                            'sentiment_label': sentiment_label,
                            'sentiment_': sentiment_score,
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
                    logging.warning(f"No reviews found for {title} (mal_id={mal_id}).")
                else:
                    logging.error(f"HTTP Error fetching reviews for {title}: {e}")
                break
            except Exception as e:
                logging.error(f"Unexpected error for {title}: {e}")
                break
        
        all_reviews_data.extend(reviews_data)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Save all collected reviews at once
    if all_reviews_data:
        reviews_df = pd.DataFrame(all_reviews_data)
        
        # Use primary key combination for deduplication before saving
        reviews_df = reviews_df.drop_duplicates(subset=['review_id', 'anime_mal_id'], keep='first')
        
        # Use INSERT OR IGNORE via SQL to respect PRIMARY KEY constraint (review_id, anime_mal_id)
        reviews_df.to_sql('reviews', conn, if_exists='append', index=False)
        
        logging.info(f"Successfully loaded and analyzed {len(reviews_df)} reviews in total.")
    else:
        logging.info("No new reviews were fetched or processed.")


def main():
    conn = sqlite3.connect(DATABASE_NAME)
    
    # 1. Setup Database Schemas
    setup_database_schema(conn)

    # 2. Fetch and Load Anime Metadata
    print("\n--- Step 1: Fetching and Loading Anime Metadata ---")
    anime_data_tuples = fetch_and_clean_anime(NUM_TOP_ANIME) 
    
    if anime_data_tuples:
        count = load_anime_to_db(conn, anime_data_tuples)
        logging.info(f"Saved/Updated {count} anime to the 'anime' table.")
        
        # 3. Fetch, Analyze, and Load Reviews for the fetched Anime
        print("\n--- Step 2: Fetching, Analyzing, and Loading Reviews ---")
        fetch_and_load_reviews(conn, anime_data_tuples)
        
    else:
        logging.warning("Failed to fetch any anime data.")
        
    conn.close()
    print("\nPipeline finished successfully! 🚀")

if __name__ == "__main__":
    main()
