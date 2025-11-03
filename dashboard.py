# dashboard.py
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

DATABASE_NAME = "anime.db"

# --- Page Configuration ---
st.set_page_config(
    page_title="Anime Analytics Hub",
    page_icon="Anime",  # Anime-inspired icon
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Anime-Style Theme ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Roboto:wght@300;400&display=swap');
    
    .main .block-container { padding-top: 2rem; }
    .stApp { 
        background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%); 
        color: #e0e0e0; 
    }
    .metric-container { background: rgba(255, 215, 0, 0.1); border: 1px solid #fbbf24; border-radius: 12px; padding: 1rem; }
    .card { 
        background: rgba(26, 26, 46, 0.8); 
        border-radius: 16px; 
        padding: 1.5rem; 
        margin: 1rem 0; 
        box-shadow: 0 8px 32px rgba(0,0,0,0.3); 
        backdrop-filter: blur(10px); 
        border: 1px solid rgba(251, 191, 36, 0.2);
    }
    h1 { 
        color: #fbbf24; 
        font-family: 'Orbitron', monospace; 
        text-align: center; 
        text-shadow: 0 0 10px rgba(251, 191, 36, 0.5);
    }
    h2 { 
        color: #a78bfa; 
        font-family: 'Orbitron', monospace; 
        border-bottom: 2px solid #fbbf24; 
        padding-bottom: 0.5rem;
    }
    .stPlotlyChart { border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
    .sidebar .sidebar-content { background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%); }
    .stSelectbox > div > div > div { background-color: #1f2937; }
    </style>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data
def load_data():
    conn = sqlite3.connect(DATABASE_NAME)
    df = pd.read_sql_query("SELECT * FROM anime", conn)
    conn.close()
    df['genres_clean'] = df['genres'].str.split(', ').apply(lambda x: [g.strip() for g in x] if isinstance(x, str) else [])
    df['year'] = None
    if 'aired' in df.columns:
        df['year'] = df['aired'].str.extract(r'(\d{4})').astype(float)
    df['year'] = df['year'].fillna(2023)
    return df

df = load_data()

# --- Sidebar Filters ---
st.sidebar.markdown("## Control Panel")
st.sidebar.markdown("---")

all_genres = sorted(set(genre for sublist in df['genres_clean'] for genre in sublist))
selected_genres = st.sidebar.multiselect("Filter by Genres", options=all_genres, default=[])

selected_year = (1900, 2025)
if 'year' in df.columns:
    unique_years = df['year'].dropna().nunique()
    if unique_years > 1:
        min_year = int(df['year'].dropna().min())
        max_year = int(df['year'].dropna().max())
        selected_year = st.sidebar.slider("Year Range", min_value=min_year, max_value=max_year, value=(min_year, max_year))
    else:
        st.sidebar.info(f"All data from one year: {int(df['year'].dropna().min())}")

# Apply filters
filtered_df = df.copy()
if selected_genres:
    mask_genres = df['genres_clean'].apply(lambda x: any(g in x for g in selected_genres))
    filtered_df = filtered_df[mask_genres]
if 'year' in df.columns:
    filtered_df = filtered_df[(filtered_df['year'] >= selected_year[0]) & (filtered_df['year'] <= selected_year[1])]

# --- Hero Section ---
col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
with col1:
    st.markdown("<h1>Anime Analytics Hub</h1>", unsafe_allow_html=True)
    st.markdown("""
        <p style='text-align: center; font-size: 1.1rem; color: #a78bfa;'>
        Dive into the otaku universe: Trends, scores, and hidden gems from MyAnimeList's Top 500. Powered by data magic. 
        </p>
    """, unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric("Total Titles", len(df), delta=f"Top {len(df)} Analyzed")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    avg_score = df['score'].mean()
    st.metric("Avg Rating", f"{avg_score:.1f}/10", delta="Hot Takes")
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    conn = sqlite3.connect(DATABASE_NAME)
    total_reviews = pd.read_sql("SELECT COUNT(*) FROM reviews", conn).iloc[0,0]
    classified = pd.read_sql("SELECT COUNT(*) FROM reviews WHERE sentiment IS NOT NULL", conn).iloc[0,0]
    conn.close()
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric("Total Reviews", f"{total_reviews}", delta=f"{classified} classified" if classified > 0 else None)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# --- Visualizations ---
# Chart 1: Top Anime
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>Elite Tier: Top 10 by Rating</h2>", unsafe_allow_html=True)
    if not filtered_df.empty:
        top_10 = filtered_df.nlargest(10, 'score')[['title', 'score', 'genres', 'studio']]
        fig1 = px.bar(top_10, x='score', y='title', orientation='h', color='score',
                      color_continuous_scale='plasma', height=500,
                      labels={'score': 'Rating (/10)', 'title': 'Title'}, hover_data=['genres', 'studio'])
        fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', title_font_family='Orbitron')
        st.plotly_chart(fig1, width='stretch')
    else:
        st.warning("No anime match your filters.")
    st.markdown('</div>', unsafe_allow_html=True)

# Chart 2: Top Studios
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>Studio Showdown: Top Producers</h2>", unsafe_allow_html=True)
    if not filtered_df.empty:
        studios = filtered_df['studio'].str.split(', ').explode().str.strip()
        top_studios = studios.value_counts().nlargest(10)
        fig2 = px.bar(x=top_studios.values, y=top_studios.index, orientation='h', color=top_studios.values,
                      color_continuous_scale='viridis', height=500)
        fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', title_font_family='Orbitron')
        st.plotly_chart(fig2, width='stretch')
    else:
        st.warning("No anime match your filters.")
    st.markdown('</div>', unsafe_allow_html=True)

# Chart 3: Genre Pie
# --- Genre Pie (FIXED) ---
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>Genre Galaxy: Popularity Breakdown</h2>", unsafe_allow_html=True)
    
    if not filtered_df.empty:
        # Extract and clean genres
        all_genres = []
        for genres in filtered_df['genres_clean']:
            if isinstance(genres, list):
                all_genres.extend([g.strip() for g in genres if g and g.strip()])
        
        if all_genres:
            genre_counts = pd.Series(all_genres).value_counts().head(10)
            fig3 = px.pie(
                values=genre_counts.values, names=genre_counts.index, hole=0.4,
                color_discrete_sequence=px.colors.sequential.Plasma
            )
            fig3.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font_color='#e0e0e0', title_font_family='Orbitron'
            )
            st.plotly_chart(fig3, width='stretch')
        else:
            st.info("No valid genres found in filtered data.")
    else:
        st.warning("No anime match your filters.")
    st.markdown('</div>', unsafe_allow_html=True)

# Chart 4: Sentiment
# --- Sentiment Card (FINAL FIX) ---
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>Sentiment Spectrum: Fan Vibes</h2>", unsafe_allow_html=True)
    
    conn = sqlite3.connect(DATABASE_NAME)
    
    # Auto-detect correct column
    try:
        cols = pd.read_sql("PRAGMA table_info(reviews)", conn)
        join_col = None
        for c in ['anime_mal_id', 'anime_id']:
            if c in cols['name'].values:
                join_col = c
                break
        
        if not join_col:
            st.error("No anime ID column in reviews. Run `load_reviews.py`.")
        else:
            if not filtered_df.empty:
                placeholders = ','.join(['?' for _ in filtered_df['title']])
                query = f"""
                    SELECT a.title, 
                           COALESCE(AVG(r.sentiment), 0) as avg_sentiment,
                           COUNT(r.sentiment) as num_reviews
                    FROM anime a 
                    LEFT JOIN reviews r ON a.mal_id = r.{join_col}
                    WHERE a.title IN ({placeholders})
                    GROUP BY a.id 
                    HAVING COUNT(r.sentiment) > 0
                    ORDER BY avg_sentiment DESC 
                    LIMIT 10
                """
                df_sent = pd.read_sql(query, conn, params=filtered_df['title'].tolist())
            else:
                df_sent = pd.DataFrame()
            
            conn.close()

            if not df_sent.empty:
                fig = px.bar(df_sent, x='title', y='avg_sentiment', color='avg_sentiment',
                             color_continuous_scale='RdYlGn', height=400,
                             hover_data=['num_reviews'])
                fig.update_layout(font_color='#e0e0e0', title_font_family='Orbitron')
                st.plotly_chart(fig, width='stretch')
                st.caption(f"{df_sent['num_reviews'].sum()} reviews")
            else:
                st.info("Run `python src/sentiment_classifier.py` first!")
    except Exception as e:
        st.error(f"DB error: {e}")
        conn.close()
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- Raw Data ---
with st.expander("Raw Data Portal", expanded=False):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if not filtered_df.empty:
        cols = ['title', 'score', 'genres', 'studio']
        if 'year' in filtered_df.columns: cols.append('year')
        st.dataframe(filtered_df[cols].style.background_gradient(cmap='plasma', subset=['score']).format({'score': '{:.1f}'}), width='stretch')
    else:
        st.info("No data.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- Footer ---
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #a78bfa; font-size: 0.9rem;'>
    Built with Streamlit & Love for Anime | Data via Jikan API | Explore the shadows. 
    </div>
""", unsafe_allow_html=True)
