import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

import sys
sys.path.append("src")

# NEW: import the recommender engine
from recommender import build_recommender, get_recommendations

DATABASE_NAME = "anime.db"

# --- Page Configuration ---
st.set_page_config(
    page_title="Anime Analytics Hub",
    page_icon="⭐", # Changed page_icon to an emoji
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Roboto:wght&display=swap');
    
    .main .block-container { padding-top: 2rem; }
    .stApp { 
        background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%); 
        color: #e0e0e0; 
    }
    /* ENHANCED METRIC CARD STYLES */
    .metric-container { 
        background: rgba(255, 215, 0, 0.15); 
        border: 2px solid #fbbf24; 
        border-radius: 12px; 
        padding: 1rem; 
        margin-top: 1rem;
        box-shadow: 0 0 10px rgba(251, 191, 36, 0.4);
    }
    .card { 
        background: rgba(26, 26, 46, 0.8); 
        border-radius: 16px; 
        padding: 1.5rem; 
        margin: 1rem 0; 
        box-shadow: 0 8px 32px rgba(0,0,0,0.3); 
        backdrop-filter: blur(10px); 
        border: 1px solid rgba(251, 191, 36, 0.2);
    }
    /* Recommendation Card Style */
    .recommendation-card {
        background: rgba(40, 40, 60, 0.9);
        border: 1px solid #a78bfa;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        transition: transform 0.2s;
        /* Ensure card takes full available width in its container */
        width: 100%; 
    }
    .recommendation-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(167, 139, 250, 0.2);
    }
    .rec-title {
        color: #fbbf24;
        font-weight: 700;
        font-size: 1.25rem;
    }
    .rec-details {
        font-size: 0.9rem;
        color: #b3b3c9;
    }
    .rec-score {
        color: #ff8c00;
        font-weight: bold;
    }
    h1 { 
        color: #fbbf24; 
        font-family: 'Orbitron', monospace; 
        text-align: center; 
        text-shadow: 0 0 15px rgba(251, 191, 36, 0.7);
    }
    h2 { 
        color: #a78bfa; 
        font-family: 'Orbitron', monospace; 
        border-bottom: 2px solid #a78bfa; /* Changed border color for contrast */
        padding-bottom: 0.5rem;
        font-size: 1.8rem;
    }
    h3 {
        color: #e0e0e0;
        font-family: 'Orbitron', monospace;
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
    
    # Check if 'reviews' table exists and load it to inspect columns later
    reviews_exists_q = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'", conn)
    reviews_exists = reviews_exists_q.empty
    
    # Load all reviews for a check
    df_reviews = None
    reviews_cols = []
    if not reviews_exists:
        try:
             # Get column info from reviews table
             reviews_cols = pd.read_sql_query("PRAGMA table_info(reviews)", conn)['name'].tolist()
             df_reviews = pd.read_sql_query("SELECT * FROM reviews", conn)
        except Exception:
             df_reviews = pd.DataFrame() # Handle case where reviews table is empty or broken

    conn.close()

    # --- FIX for Genre Extraction Error ---
    if 'genres' in df.columns:
        df['genres_clean'] = df['genres'].astype(str).str.split(', ').apply(
            lambda x: [g.strip() for g in x if g.strip()] if isinstance(x, list) else 
                       ([g.strip() for g in x.split(', ') if g.strip()] if isinstance(x, str) else [])
        )
    else:
        df['genres_clean'] = [[]] * len(df)
        
    df['year'] = None
    if 'aired' in df.columns:
        # Fixed regex to safely extract year
        df['year'] = df['aired'].astype(str).str.extract(r'(\d{4})').astype(float)
    df['year'] = df['year'].fillna(2023).astype(int) # Ensure year is integer for grouping
    
    return df, df_reviews, reviews_cols

df, df_reviews, reviews_cols = load_data()


# --- Sidebar Filters ---
st.sidebar.markdown("## Control Panel")
st.sidebar.markdown("---")

# Genre Filter
all_genres = sorted(set(genre for sublist in df['genres_clean'] for genre in sublist))
selected_genres = st.sidebar.multiselect("Filter by Genres", options=all_genres, default=[])

# Year Filter 
selected_year = (1900, 2025)
if 'year' in df.columns and not df['year'].dropna().empty:
    min_year = int(df['year'].dropna().min())
    max_year = int(df['year'].dropna().max()) # Fixed logic error here (was min())
    
    # Safety buffer for Streamlit Slider if min/max are the same
    if min_year == max_year:
        min_year = max(1900, min_year - 1) 
        
    selected_year = st.sidebar.slider("Year Range", min_value=min_year, max_value=max_year, value=(min_year, max_year))

# Filtering Logic
filtered_df = df.copy()
if selected_genres:
    mask = filtered_df['genres_clean'].apply(lambda x: any(g in x for g in selected_genres))
    filtered_df = filtered_df[mask]
filtered_df = filtered_df[(filtered_df['year'] >= selected_year[0]) & (filtered_df['year'] <= selected_year[1])]

# --- Hero Metrics ---
st.markdown("<h1>Anime Analytics Hub</h1>", unsafe_allow_html=True)
st.markdown("""
    <p style='text-align: center; font-size: 1.1rem; color: #a78bfa;'>
    Dive into the otaku universe: Trends, scores, and hidden gems powered by data magic.
    </p>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric("Total Titles", len(df), delta=f"Filtered: {len(filtered_df)}")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric("Avg Rating", f"{df['score'].mean():.2f}/10")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    # Use the loaded df_reviews for safety checks
    total_reviews = len(df_reviews) if df_reviews is not None and not df_reviews.empty else 0
    # **FIX: Using 'sentiment_' column for classified count based on review table inspection**
    classified = df_reviews['sentiment_'].count() if df_reviews is not None and 'sentiment_' in df_reviews.columns else 0
    
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric("Total Reviews", f"{total_reviews:,}", delta=f"{classified:,} classified")
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    # Total Producers (unique studios)
    total_studios = filtered_df['studio'].str.split(', ').explode().nunique()
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric("Unique Producers", f"{total_studios:,}")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# --- TAB STRUCTURE: ADDING NEW TAB 6 ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "⭐ Overview & Rating", 
    "🪐 Genre Trends", 
    "⚔️ Studio Analysis", 
    "💬 Sentiment Spectrum", 
    "🤖 Recommendation Engine",
    "📈 Temporal Trends"
])

# --- VISUALIZATION 1: Top Anime ---
with tab1:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h2>Elite Tier: Top 10 by Rating</h2>", unsafe_allow_html=True)
        if not filtered_df.empty:
            top_10 = filtered_df.nlargest(10, 'score')[['title', 'score', 'genres', 'studio']]
            fig = px.bar(
                top_10, x='score', y='title', orientation='h', color='score',
                color_continuous_scale='plasma', height=500,
                labels={'score': 'Rating (/10)', 'title': 'Title'}, hover_data=['genres', 'studio']
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data matches the current filters in the control panel.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- VISUALIZATION 2: Genre Analysis (Pie Chart + Scatter Plot) ---
with tab2:
    # Removed st.columns(2) to stack the plots and use full width
    
    # --- 2A: Genre Popularity Pie Chart ---
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h3>Genre Galaxy: Top 10 Popularity Breakdown</h3>", unsafe_allow_html=True)

        if not filtered_df.empty:
            all_gen = []
            for g in filtered_df['genres_clean']:
                all_gen.extend(g)
            
            if all_gen:
                genre_counts = pd.Series(all_gen).value_counts().head(10)

                fig = px.pie(
                    values=genre_counts.values, names=genre_counts.index,
                    hole=0.4, color_discrete_sequence=px.colors.sequential.Plasma
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("The filtered data contains titles, but no valid genres could be extracted from them.")
        else:
             st.warning("No data matches the current filters in the control panel.")

        st.markdown('</div>', unsafe_allow_html=True)
        
    # --- 2B: Genre Score vs Count Scatter Plot (FIXED) ---
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h3>Genre Score vs. Production Volume Scatter Plot</h3>", unsafe_allow_html=True)
        
        if not filtered_df.empty:
            # Explode the DataFrame by genre
            exploded_df = filtered_df.explode('genres_clean')
            
            # Calculate metrics per genre
            genre_metrics = exploded_df.groupby('genres_clean').agg(
                avg_score=('score', 'mean'),
                count=('title', 'count')
            ).reset_index()
            
            # Create the scatter plot
            fig_scatter = px.scatter(
                genre_metrics,
                x='avg_score',
                y='count',
                color='avg_score',
                size='count',
                hover_name='genres_clean',
                color_continuous_scale='RdYlBu', # A divergent color scale for scores
                labels={'avg_score': 'Average Score', 'count': 'Number of Titles (Count)'},
                title='Average Score vs. Production Volume by Genre'
            )

            # Customize layout for dark theme
            fig_scatter.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#e0e0e0"),
                xaxis=dict(gridcolor='#333344'),
                yaxis=dict(gridcolor='#333344')
            )
            
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.warning("No data matches the current filters in the control panel.")

        st.markdown('</div>', unsafe_allow_html=True)

# --- VISUALIZATION 3: Top Studios ---
with tab3:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h2>Studio Showdown: Top Producers</h2>", unsafe_allow_html=True)

        if not filtered_df.empty:
            studios = filtered_df['studio'].str.split(', ').explode().str.strip()
            top_studios = studios.value_counts().nlargest(10)
            fig = px.bar(
                x=top_studios.values, y=top_studios.index, orientation='h',
                color=top_studios.values, color_continuous_scale='viridis', height=500
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data matches the current filters in the control panel.")

        st.markdown('</div>', unsafe_allow_html=True)

# --- VISUALIZATION 4: Sentiment Spectrum (IMPROVED ERROR HANDLING & COLUMN NAME) ---
with tab4:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h2>Sentiment Spectrum: Fan Vibes</h2>", unsafe_allow_html=True)

        # Check for the required columns in the reviews table
        required_cols = ['sentiment_', 'anime_mal_id'] 
        missing_cols = [col for col in required_cols if col not in reviews_cols]
        
        if 'anime_mal_id' in missing_cols:
            st.error(
                f"🚨 **Data Pipeline Error**: The reviews table is missing the required foreign key column **`anime_mal_id`** to link reviews to anime titles. "
                f"This must be added by running `load_reviews.py` successfully."
            )
        else:
            conn = sqlite3.connect(DATABASE_NAME)
            
            # Use mal_id for parameter binding, which is much safer and easier to handle in SQL
            mal_ids = filtered_df['mal_id'].tolist()
            placeholders = ','.join('?' for _ in mal_ids)
            
            # **FIX: Corrected SQL query to use 'r.sentiment_' instead of 'r.sentiment'**
            query = f"""
                SELECT a.title,
                       COALESCE(AVG(r.sentiment_), 0) AS avg_sentiment, 
                       COUNT(r.sentiment_) AS num_reviews
                FROM anime a
                LEFT JOIN reviews r ON CAST(a.mal_id AS TEXT) = CAST(r.anime_mal_id AS TEXT)
                WHERE a.mal_id IN ({placeholders})
                GROUP BY a.mal_id, a.title
                HAVING COUNT(r.sentiment_) > 0
                ORDER BY avg_sentiment DESC
                LIMIT 10
            """
            try:
                # Need to check if there are IDs before querying the database
                if mal_ids:
                    # Pass mal_ids directly as parameters to prevent SQL injection and handle complex titles
                    df_sent = pd.read_sql(query, conn, params=mal_ids)
                else:
                    df_sent = pd.DataFrame()
            except Exception as e:
                # Provide a more detailed error message for debugging
                st.error(f"DB Execution error in Sentiment Spectrum. Check your column names or the mal_id data types: {e}")
                df_sent = pd.DataFrame()
                
            conn.close()

            if not df_sent.empty:
                fig = px.bar(
                    df_sent, x='title', y='avg_sentiment', color='avg_sentiment',
                    color_continuous_scale='RdYlGn', height=400,
                    labels={'avg_sentiment': 'Avg. Sentiment Score', 'title': 'Title'},
                    hover_data=['num_reviews']
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No classified reviews found for the filtered anime titles, or titles not found in the database.")

        st.markdown('</div>', unsafe_allow_html=True)


# --- VISUALIZATION 5: Recommender Engine ---
with tab5:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h2>🤖 Anime Recommendation Engine</h2>", unsafe_allow_html=True)

        # Ensure only titles from the filtered dataframe are used for the recommender dropdown
        titles = filtered_df['title'].tolist() if not filtered_df.empty else df['title'].tolist()
        
        selected_anime = st.selectbox("Choose an anime to find similar titles:", titles)

        if st.button("Recommend Similar Anime", type="primary"):
            with st.spinner("Building recommendation model and fetching results..."):
                # Check if there's enough data to build the model
                if len(df) < 2:
                     st.warning("Not enough data loaded to build a reliable recommender. Load more anime data!")
                else:
                    # Note: You need to ensure the recommender.py is in the 'src' directory
                    try:
                        sim_matrix = build_recommender(df, use_studio=True, use_score=True)
                        results = get_recommendations(selected_anime, df, sim_matrix, top_n=10)
                    except Exception as e:
                        st.error(f"Error during recommendation generation: {e}")
                        results = None

                    if results is not None and not results.empty:
                        st.success(f"Top {len(results)} recommendations similar to **{selected_anime}**:")
                        
                        # --- UI Cooler Output (MODIFIED: Use single full-width column) ---
                        
                        for i, row in results.iterrows():
                            # Removed the st.columns(2) and used st.container() for full width
                            
                            # Ensure similarity is between 0 and 1 for clean percentage display
                            similarity_percent = f"{min(row['similarity'] * 100, 100):.1f}%"
                            
                            st.markdown(f"""
                            <div class="recommendation-card">
                                <div class="rec-title">#{i+1}: {row['title']}</div>
                                <div class="rec-details">
                                    <p>
                                        ⭐ Rating: <span class="rec-score">{row['score']:.2f}/10</span> | 
                                        🔗 Similarity: <span class="rec-score">{similarity_percent}</span>
                                    </p>
                                    <p>
                                        🏭 Studio: {row['studio']}
                                    </p>
                                    <p>
                                        📚 Genres: {row['genres']}
                                    </p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.warning("Could not find recommendations for the selected anime.")

        st.markdown('</div>', unsafe_allow_html=True)


# --- VISUALIZATION 6: Temporal Trends (NEW) ---
with tab6:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h2>Production Timeline: Releases Per Year</h2>", unsafe_allow_html=True)

        if not filtered_df.empty:
            # 1. Group by year and count the number of anime titles
            trend_df = filtered_df.groupby('year').size().reset_index(name='count')
            
            # 2. Sort by year (important for time series)
            trend_df = trend_df.sort_values('year')

            # 3. Create the Plotly Area Chart
            fig = px.area(
                trend_df,
                x='year',
                y='count',
                title='Anime Releases Over Time (Filtered)',
                labels={'year': 'Year of Release', 'count': 'Number of Anime Titles'},
                color_discrete_sequence=['#a78bfa'], # Use a complementary color
                line_shape='spline', # Smooth the curve
                height=500
            )
            
            # Customize the layout for dark mode
            fig.update_layout(
                xaxis_title="Release Year",
                yaxis_title="Number of Titles",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#e0e0e0"),
                hovermode="x unified"
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
             st.warning("No data matches the current filters in the control panel.")

        st.markdown('</div>', unsafe_allow_html=True)

# --- Footer ---
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #a78bfa; font-size: 0.9rem;'>
    Built with Streamlit & Love for Anime | Data via Jikan API 
    </div>
""", unsafe_allow_html=True)
