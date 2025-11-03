# src/load_reviews.py
import sqlite3
import time
import requests
from tqdm import tqdm
from database_setup import DATABASE_NAME, create_database

create_database()  # Ensure tables exist

# Connect to DB
conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

N = 20
cursor.execute("SELECT id, mal_id FROM anime ORDER BY score DESC LIMIT ?", (N,))
anime_list = cursor.fetchall()

print(f"Fetching reviews for top {N} anime... ({len(anime_list)} available)")

if not anime_list:
    print("No anime data! Run load_data.py first.")
    conn.close()
    exit(1)

reviews_inserted = 0
skipped_reviews = 0

for anime_id, mal_id in tqdm(anime_list, desc="Anime"):
    try:
        url = f"https://api.jikan.moe/v4/anime/{mal_id}/reviews"
        all_reviews = []
        
        while url:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and data['data']:
                all_reviews.extend(data['data'])
                url = data.get('pagination', {}).get('next', None)
            else:
                url = None
        
        reviews = all_reviews[:50]  # Cap at 50 per anime
        loaded_this_anime = 0
        
        for review in reviews:
            review_text = review.get('review', '') or review.get('body', '') or ""
            reviewer_name = (
                review.get('user', {}).get('username') or
                review.get('reviewer', {}).get('username') or
                "Anonymous"
            )
            date = review.get('date', '') or ""

            if len(review_text) > 5:
                # FIXED: Use UNIQUE constraint + OR IGNORE
                cursor.execute("""
                    INSERT OR IGNORE INTO reviews (anime_mal_id, review_text, reviewer_name, date)
                    VALUES (?, ?, ?, ?)
                """, (mal_id, review_text, reviewer_name, date))
                
                if cursor.rowcount > 0:
                    loaded_this_anime += 1
                    reviews_inserted += 1
            else:
                skipped_reviews += 1
        
        if loaded_this_anime > 0:
            print(f"Loaded {loaded_this_anime} reviews for mal_id={mal_id}")
        else:
            print(f"No valid reviews for mal_id={mal_id} (fetched {len(reviews)})")
        
        time.sleep(0.5)  # Be nice to Jikan API
        
    except Exception as e:
        print(f"Error for mal_id={mal_id}: {e}")
        continue

# Add UNIQUE constraint if not exists (prevents duplicates)
cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_review 
    ON reviews (anime_mal_id, review_text(200))
""")

conn.commit()
conn.close()

print(f"\nLoaded {reviews_inserted} reviews total! (Skipped {skipped_reviews}).")
print(f"Verify: sqlite3 {DATABASE_NAME} 'SELECT COUNT(*) FROM reviews;'")
