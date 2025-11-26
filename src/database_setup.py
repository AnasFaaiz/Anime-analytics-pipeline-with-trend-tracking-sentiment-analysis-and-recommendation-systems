import sqlite3

DATABASE_NAME = "anime.db"

def create_database():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Drop old tables to ensure we start fresh with new columns
    cursor.execute("DROP TABLE IF EXISTS anime")
    cursor.execute("DROP TABLE IF EXISTS reviews")

    # ANIME TABLE (Updated with image_url and synopsis)
    cursor.execute("""
    CREATE TABLE anime (
        mal_id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        score REAL,
        episodes INTEGER,
        status TEXT,
        genres TEXT,
        studio TEXT,
        aired TEXT,
        image_url TEXT,  -- <--- This is the column you were missing
        synopsis TEXT,
        popularity INTEGER,
        members INTEGER
    );
    """)

    # REVIEWS TABLE
    cursor.execute("""
    CREATE TABLE reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        anime_mal_id INTEGER,
        review_text TEXT NOT NULL,
        reviewer_name TEXT,
        date TEXT,
        score INTEGER,
        sentiment_label TEXT,
        sentiment_score REAL,
        FOREIGN KEY (anime_mal_id) REFERENCES anime(mal_id) ON DELETE CASCADE
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_anime ON reviews(anime_mal_id);")

    conn.commit()
    conn.close()
    print(f"Database `{DATABASE_NAME}` created/reset with improved schema.")

if __name__ == "__main__":
    create_database()
