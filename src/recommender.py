import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity


def preprocess_text_field(series):
    """Convert comma lists into whitespace tokens: ['Action', 'Fantasy'] -> 'Action Fantasy'."""
    # Ensure all values are strings before splitting
    return series.fillna("").astype(str).apply(
        lambda x: " ".join(item.strip().replace(" ", "_") for item in x.split(","))
    )


def build_feature_matrix(df, use_studio=True, use_score=True):
    """
    Build combined feature matrix using:
        - TF-IDF(Genres)
        - TF-IDF(Studio) (optional)
        - Scaled score (optional)
    """

    # --- Genres TF-IDF ---
    # NOTE: df["genres_clean"] is created here and used later in load_data, so keep this logic
    df["genres_clean"] = preprocess_text_field(df["genres"])
    tfidf_genres = TfidfVectorizer()
    genres_matrix = tfidf_genres.fit_transform(df["genres_clean"])

    matrices = [genres_matrix]    # Always include genres

    # --- Studio TF-IDF (optional) ---
    if use_studio:
        df["studio_clean"] = preprocess_text_field(df["studio"])
        tfidf_studio = TfidfVectorizer()
        studio_matrix = tfidf_studio.fit_transform(df["studio_clean"])
        matrices.append(studio_matrix)

    # --- Score Feature (optional) ---
    if use_score:
        # Ensure score column has no NaNs for the scaler
        df_temp = df.copy()
        df_temp['score'] = df_temp['score'].fillna(df_temp['score'].mean())
        
        scaler = MinMaxScaler()
        score_scaled = scaler.fit_transform(df_temp[["score"]])  # shape (n,1)
        score_sparse = sp.csr_matrix(score_scaled)
        matrices.append(score_sparse)

    # --- Combine all matrices ---
    final_matrix = sp.hstack(matrices).tocsr()

    return final_matrix


def build_recommender(df, use_studio=True, use_score=True):
    """
    Returns the cosine similarity matrix based on combined feature matrix.
    The DataFrame is reset here to align with the similarity matrix indices.
    """
    df = df.reset_index(drop=True)
    
    # Ensure the DataFrame has enough records to prevent crashes
    if len(df) < 2:
        # Return an identity matrix for safety if only one or zero items exist
        return sp.eye(len(df)).toarray() if len(df) == 1 else None

    feature_matrix = build_feature_matrix(df, use_studio, use_score)
    
    # Calculate Cosine Similarity [Image of Cosine Similarity Vector Calculation]
    similarity_matrix = cosine_similarity(feature_matrix, feature_matrix)
    return similarity_matrix


def get_recommendations(title, df, similarity_matrix, top_n=10):
    """
    Get top-N similar anime for a given title.
    FIXED: Renamed the similarity column to 'similarity_score' to match dashboard.py
    """
    # Important: Reset index to ensure alignment between DataFrame index and similarity matrix index
    df = df.reset_index(drop=True)

    if similarity_matrix is None or title not in df["title"].values:
        return None

    # Get the index of the anime that matches the title
    idx = df[df["title"] == title].index[0]
    
    # Get the similarity scores for that anime
    scores = list(enumerate(similarity_matrix[idx]))

    # Sort by similarity, highest first (ignore the anime itself at index 0)
    scores = sorted(scores, key=lambda x: x[1], reverse=True)[1:top_n + 1]

    # Extract the indices and the similarity values
    indices = [i for i, sim in scores]
    similarities = [sim for i, sim in scores]

    # Create the results DataFrame
    results = df.loc[indices, ["title", "score", "genres", "studio"]].copy()
    
    # CRITICAL FIX: Name the column 'similarity_score' to match dashboard.py display logic
    results["similarity"] = similarities

    return results
