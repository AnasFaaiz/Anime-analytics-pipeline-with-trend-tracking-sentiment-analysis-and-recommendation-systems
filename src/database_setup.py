# src/database_setup.py
import sqlite3

DATABASE_NAME = "anime.db"

def create_database():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # === ANIME TABLE ===
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS anime (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mal_id INTEGER UNIQUE NOT NULL,
        title TEXT NOT NULL,
        score REAL,
        episodes INTEGER,
        status TEXT,
        genres TEXT,
        studio TEXT,
        aired TEXT
    );
    """)

    # === REVIEWS TABLE ===
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        anime_mal_id INTEGER,
        review_text TEXT NOT NULL,
        reviewer_name TEXT,
        date TEXT,
        sentiment REAL,
        sentiment_score REAL,
        -- Generated column: first 200 chars of review_text
        review_text_preview TEXT GENERATED ALWAYS AS (substr(review_text, 1, 200)) VIRTUAL,
        FOREIGN KEY (anime_mal_id) REFERENCES anime(mal_id) ON DELETE CASCADE
    );
    """)

    # === INDEXES ===
    # Fast lookup by anime
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_anime ON reviews(anime_mal_id);")
    
    # Prevent duplicate reviews (same anime + same first 200 chars)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_review 
        ON reviews (anime_mal_id, review_text_preview)
    """)

    conn.commit()
    conn.close()
    print(f"Database `{DATABASE_NAME}` created successfully with safe unique index.")

if __name__ == "__main__":
    create_database()
