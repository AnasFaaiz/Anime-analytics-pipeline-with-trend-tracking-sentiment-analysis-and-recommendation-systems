import sqlite3
import time
from data_fetcher import fetch_top_anime, fetch_anime_reviews
from database_setup import DATABASE_NAME, create_database

def clean_and_prepare_anime(anime_list):
    """Cleans raw anime data for DB insertion."""
    prepared_data = []
    for anime in anime_list:
        genres = ", ".join([g['name'] for g in anime.get('genres', [])])
        studios = ", ".join([s['name'] for s in anime.get('studios', [])])
        
        # Handle safely getting nested data
        aired = anime.get('aired', {}).get('string', 'Unknown')
        image_url = anime.get('images', {}).get('jpg', {}).get('image_url', None)
        synopsis = anime.get('synopsis', 'No synopsis available.')

        prepared_data.append((
            anime.get('mal_id'),
            anime.get('title'),
            anime.get('score', 0),
            anime.get('episodes', 0),
            anime.get('status', 'Unknown'),
            genres,
            studios,
            aired,
            image_url,
            synopsis,
            anime.get('popularity', 0),
            anime.get('members', 0)
        ))
    return prepared_data

def load_anime_to_db(data):
    """Inserts anime metadata into the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.executemany("""
    INSERT OR REPLACE INTO anime 
    (mal_id, title, score, episodes, status, genres, studio, aired, image_url, synopsis, popularity, members)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    
    conn.commit()
    count = cursor.rowcount
    conn.close()
    return count

def load_reviews_for_anime(anime_list):
    """Loops through anime list, fetches reviews, and saves them."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    print("\n--- Starting Review Fetching (This takes time!) ---")
    
    total_reviews_added = 0
    
    for index, anime in enumerate(anime_list):
        mal_id = anime[0] # getting mal_id from the tuple we created earlier
        title = anime[1]
        
        print(f"[{index+1}/{len(anime_list)}] Fetching reviews for: {title}...")
        
        reviews = fetch_anime_reviews(mal_id)
        
        if reviews:
            # Prepare review data for SQL
            review_tuples = [(r['anime_mal_id'], r['review_text'], r['reviewer_name'], r['date'], r['score']) for r in reviews]
            
            cursor.executemany("""
            INSERT OR IGNORE INTO reviews (anime_mal_id, review_text, reviewer_name, date, score)
            VALUES (?, ?, ?, ?, ?)
            """, review_tuples)
            
            total_reviews_added += len(reviews)
            conn.commit() # Commit often so we don't lose data if script stops
        
        # CRITICAL: Sleep to avoid getting banned by Jikan API
        time.sleep(1.5) 

    conn.close()
    print(f"\nSuccessfully loaded {total_reviews_added} reviews in total.")

if __name__ == "__main__":
    # 1. Reset Database
    create_database()
    
    # 2. Fetch and Load Anime
    print("\nStep 1: Fetching Anime Metadata...")
    raw_anime = fetch_top_anime(pages=2, limit=25) # Reduced pages for testing, set to 4 for full run
    
    if raw_anime:
        clean_anime = clean_and_prepare_anime(raw_anime)
        count = load_anime_to_db(clean_anime)
        print(f"Saved {count} anime to database.")
        
        # 3. Fetch and Load Reviews for those Anime
        print("\nStep 2: Fetching Reviews...")
        load_reviews_for_anime(clean_anime)
        
    else:
        print("Failed to fetch anime data.")
        
    print("\nPipeline finished successfully! 🚀")
