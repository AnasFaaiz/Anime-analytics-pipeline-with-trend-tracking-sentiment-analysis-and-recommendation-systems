# src/sentiment_classifier.py
from transformers import pipeline
from tqdm import tqdm
import sqlite3
import pandas as pd

# Load model
print("Loading sentiment model...")
classifier = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
    device=-1  # CPU
)

# Load reviews
conn = sqlite3.connect("anime.db")
df = pd.read_sql("""
    SELECT review_id, review_text 
    FROM reviews 
    WHERE review_text IS NOT NULL 
      AND LENGTH(review_text) > 10
""", conn)
conn.close()

print(f"Classifying {len(df)} reviews...")

sentiments = []
scores = []

for text in tqdm(df["review_text"]):
    res = classifier(text[:512])[0]
    label = res["label"]
    score = res["score"]

    # Map LABEL_2 → 1.0, LABEL_0 → 0.0
    if label == "LABEL_2":
        sentiment = 1.0
    elif label == "LABEL_0":
        sentiment = 0.0
    else:
        sentiment = 0.5

    sentiments.append(sentiment)
    scores.append(score)

df["sentiment"] = sentiments
df["sentiment_score"] = scores

# Save back safely
conn = sqlite3.connect("anime.db")
cur = conn.cursor()

# Add columns if missing
cols = [row[1] for row in cur.execute("PRAGMA table_info(reviews)").fetchall()]
if 'sentiment' not in cols:
    cur.execute("ALTER TABLE reviews ADD COLUMN sentiment REAL")
if 'sentiment_score' not in cols:
    cur.execute("ALTER TABLE reviews ADD COLUMN sentiment_score REAL")
conn.commit()

df.to_sql("reviews", conn, if_exists="replace", index=False)
conn.close()

print(f"DONE! Avg sentiment: {df['sentiment'].mean():.1%} positive")
