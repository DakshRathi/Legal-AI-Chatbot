# ml_core/embeddings.py
from langchain_community.embeddings import JinaEmbeddings
from app.core.config import settings

# Configuration - Define model name here or rely on LangChain's default
# Use v2 as it's consistently documented in Python examples
# LangChain's default is 'jina-embeddings-v2-base-en'
JINA_MODEL_NAME = "jina-embeddings-v2-base-en"

# --- Singleton Instance ---
_embedding_model = None

def get_embedding_model() -> JinaEmbeddings:
    """Initializes and returns the LangChain Jina embedding model instance."""
    global _embedding_model
    if _embedding_model is None:
        print(f"Initializing LangChain JinaEmbeddings client (Model: {JINA_MODEL_NAME})...")

        # Ensure API key is available
        jina_api_key = settings.JINA_API_KEY
        if not jina_api_key or not jina_api_key.startswith("jina_"):
             raise ValueError("JINA_API_KEY is not configured correctly in settings/environment.")

        # Instantiate the LangChain class
        _embedding_model = JinaEmbeddings(
            jina_api_key=jina_api_key,
            model_name=JINA_MODEL_NAME
        )
        print("LangChain JinaEmbeddings client initialized.")
    return _embedding_model

# --- Basic Test Block (Optional) ---
if __name__ == '__main__':
    print("Attempting to initialize embedding model...")
    try:
        model = get_embedding_model()
        print("Model initialized successfully.")
        # Optional: Test embedding a single query synchronously
        print("Testing sync embed_query...")
        test_query = "This is a test query."
        embedding = model.embed_query(test_query)
        print(f"Successfully embedded query. Dimension: {len(embedding)}")
    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"Error during initialization or test: {e}")

