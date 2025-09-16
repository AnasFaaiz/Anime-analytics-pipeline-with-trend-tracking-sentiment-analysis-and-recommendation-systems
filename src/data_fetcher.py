import requests
import time

API_URL = "https://api.jikan.moe/v4/top/anime"

def fetch_top_anime(pages=1):
    """Fetch the top anime from the Jikan API for a given number of pages."""
    all_anime = []
    for page in range(1, pages + 1):
        print(f"Fetching page {page}...")
        try:
            response = requests.get(API_URL, params={"page": page })
            response.raise_for_status()
            data = response.json()
            all_anime.extend(data.get("data", []))
            time.sleep(1)
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            break
    return all_anime

def fetch_anime_reviews(anime_id):
    """Fetches reviews for a specific anime from the Jikan API"""
    reviews_url = f"https://api.jikan.moe/v4/anime/{anime_id}/reviews"
    try:
        print(f"fteching reviews for anime ID {anime_id}..")
        response = requests.get(reviews_url)
        response.raise_for_status()
        data = response.json()

        reviews = [
            (anime_id, review['review'])
            for review in data.get("data", [])
        ]
        time.sleep(1)
        return reviews
    except requests.execptions.RequestException as e:
        print(f"An error occurred while fetching reviews for anime ID {anime_id}..")
        return []

if __name__ == "__main__":
    top_anime_data = fetch_top_anime(pages=4)
    if top_anime_data:
        print(f"Successfully fetched {len(top_anime_data)} anime entries.")
