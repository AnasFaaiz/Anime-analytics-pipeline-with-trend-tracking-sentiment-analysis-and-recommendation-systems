import sqlite3, pandas as pd, numpy as np
from sentence_transformers import SentenceTransformer, util
from sklearn.preprocessing import MinMaxScaler
import streamlit as st

# BEST MODEL FOR YOU
model = SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_data
def get_recommendations(anime_title: str, top_k: int = 5):
    conn = sqlite3.connect("anime.db")
    df = pd.read_sql("""
        SELECT a.id, a.title, a.genres, a.score,
               COALESCE(AVG(r.sentiment), 0.5) AS avg_sentiment
        FROM anime a
        LEFT JOIN reviews r ON a.id = r.anime_id
        GROUP BY a.id
    """, conn)
    conn.close()

    # Text to embed
    df["text"] = df["title"] + " " + df["genres"].fillna("") + " sentiment:" + df["avg_sentiment"].round(2).astype(str)

    # Embed
    embeddings = model.encode(df["text"].tolist(), convert_to_tensor=True)

    # Find target
    target_idx = df[df["title"] == anime_title].index[0]
    target_emb = embeddings[target_idx]

    # Cosine similarity
    sims = util.cos_sim(target_emb, embeddings)[0].cpu().numpy()
    sims[target_idx] = -1  # remove self
    top_idx = np.argsort(-sims)[:top_k]

    recs = df.iloc[top_idx][["title", "score", "avg_sentiment", "genres"]].copy()
    recs["similarity"] = sims[top_idx]
    return recs.reset_index(drop=True)
