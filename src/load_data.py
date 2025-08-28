import sqlite3
from data_fetcher import fetch_top_anime
from database_setup import DATABASE_NAME

def clean_and_prepare_data(anime_list):
    """Cleans the raw data and prepares it for database insertion."""
    prepared_data = []
    for anime in anime_list:
        genres = ", ".join([genre['name'] for genre in anime.get('genres', [])])
        studios = ", ".join([studio['name'] for studio in anime.get('studios', [])])

        prepared_data.append((
            anime.get('mal_id'),
            anime.get('title'),
            anime.get('score'),
            anime.get('episodes'),
            anime.get('status'),
            genres,
            studios 
        ))
    return prepared_data

def load_data_to_db(data):
    """Loads the prepared data into the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.executemany("""
    INSERT OR IGNORE INTO anime (mal_id, title, score, episodes, status, genres, studio)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    print(f"Successfully loaded {cursor.rowcount} new entries into the database.")
    conn.close()

if __name__ == "__main__":
    print("Starting data pipline...")
    raw_data = fetch_top_anime(pages=4)
    if raw_data:
        prepared_data = clean_and_prepare_data(raw_data)
        load_data_to_db(prepared_data)
    print("Pipeline finished.")
