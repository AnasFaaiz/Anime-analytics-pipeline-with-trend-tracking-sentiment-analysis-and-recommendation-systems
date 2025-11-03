import requests
import time

API_URL = "https://api.jikan.moe/v4/top/anime"

def fetch_top_anime(pages=4, limit=25):
    """Fetch the top anime from the Jikan API."""
    all_anime = []
    for page in range(1, pages + 1):
        print(f"Fetching page {page}...")
        try:
            response = requests.get(API_URL, params={"page": page, "limit": limit})
            response.raise_for_status()
            data = response.json()
            anime_page = data.get("data", [])
            all_anime.extend(anime_page)
            print(f"Page {page}: {len(anime_page)} anime fetched.")
        except requests.exceptions.RequestException as e:
            print(f"Error on page {page}: {e}")
            break
        time.sleep(1)  # Rate limit
    return all_anime

def fetch_anime_reviews(mal_id):
    """Fetches reviews for a specific anime."""
    reviews_url = f"https://api.jikan.moe/v4/anime/{mal_id}/reviews"
    try:
        print(f"Fetching reviews for anime ID {mal_id}...")
        response = requests.get(reviews_url)
        response.raise_for_status()
        data = response.json()
        reviews = data.get("data", [])
        return reviews  # List of dicts with 'body', 'reviewer', 'date'
    except requests.exceptions.RequestException as e:
        print(f"Error fetching reviews for {mal_id}: {e}")
        return []
