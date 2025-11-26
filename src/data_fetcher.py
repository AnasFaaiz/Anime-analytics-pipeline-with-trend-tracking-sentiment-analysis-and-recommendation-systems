import requests
import time

API_URL = "https://api.jikan.moe/v4/top/anime"

def fetch_top_anime(pages=4, limit=25):
    """Fetch the top anime metadata from the Jikan API."""
    all_anime = []
    for page in range(1, pages + 1):
        print(f"Fetching Top Anime page {page}...")
        try:
            response = requests.get(API_URL, params={"page": page, "limit": limit})
            response.raise_for_status()
            data = response.json()
            items = data.get("data", [])
            all_anime.extend(items)
            print(f"   -> Page {page}: {len(items)} anime fetched.")
            time.sleep(1)  # Rate limit safety
        except requests.exceptions.RequestException as e:
            print(f"   -> Error on page {page}: {e}")
            break
    return all_anime

def fetch_anime_reviews(mal_id):
    """Fetches text reviews for a specific anime."""
    reviews_url = f"https://api.jikan.moe/v4/anime/{mal_id}/reviews"
    try:
        response = requests.get(reviews_url)
        response.raise_for_status()
        data = response.json()
        raw_reviews = data.get("data", [])
        
        # Clean the reviews immediately
        cleaned_reviews = []
        for r in raw_reviews:
            cleaned_reviews.append({
                'anime_mal_id': mal_id,
                'review_text': r.get('review', ''),
                'reviewer_name': r.get('user', {}).get('username', 'Anonymous'),
                'date': r.get('date', ''),
                'score': r.get('score')
            })
        return cleaned_reviews

    except requests.exceptions.RequestException as e:
        print(f"   -> Error fetching reviews for ID {mal_id}: {e}")
        return []
