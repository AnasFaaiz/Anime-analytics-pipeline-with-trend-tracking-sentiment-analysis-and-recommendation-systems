import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns

DATABASE_NAME = "anime.db"

# --- Page Configuration ---
st.set_page_config(
    page_title="Anime Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- Data Loading ---
@st.cache_data
def load_data():
    """Loads data from the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    df = pd.read_sql_query("SELECT * FROM anime", conn)
    conn.close()
    return df

df = load_data()

# --- Main Page ---
st.title("📊 Anime Analytics Dashboard")
st.markdown("Exploring trends from the Top 100 Anime on MyAnimeList.")

# --- Visualizations ---

# -- Chart 1: Top Anime by Score --
st.header("Top 10 Anime by Score")
top_10_scored = df.nlargest(10, 'score')
fig1, ax1 = plt.subplots(figsize=(10, 6))
sns.barplot(data=top_10_scored, x='score', y='title', palette='viridis', ax=ax1)
ax1.set_title('Top 10 Anime by Score')
ax1.set_xlabel('Score')
ax1.set_ylabel('Anime Title')
st.pyplot(fig1)


# -- Chart 2: Top Studios --
st.header("Top 10 Studios by Production Count")
studios = df['studio'].str.split(', ').explode().str.strip()
top_10_studios = studios.value_counts().nlargest(10)
fig2, ax2 = plt.subplots(figsize=(10, 6))
sns.barplot(x=top_10_studios.values, y=top_10_studios.index, palette='mako', ax=ax2)
ax2.set_title('Top 10 Studios by Number of Productions (in Top 100)')
ax2.set_xlabel('Number of Productions')
ax2.set_ylabel('Studio')
st.pyplot(fig2)

# -- Raw Data Viewer --
st.header("Raw Data")
st.dataframe(df)