import sqlite3

DATABASE_NAME = "anime.db"

def create_database():
    """Creates the SQLite database and the anime table."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS anime (
        mal_id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        score REAL,
        episodes INTEGER,
        status TEXT,
        genres TEXT,
        studio TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        anime_id INTEGER,
        review_text TEXT NOT NULL,
        FOREIGN KEY (anime_id) REFERENCES anime(mal_id)
    );
    """)

    conn.commit()
    conn.close()
    print(f"Database `{DATABASE_NAME}` and table 'anime', 'reviews' created successfully.")

if __name__ == "__main__":
    create_database()
