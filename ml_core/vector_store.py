# ml_core/vector_store.py
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

# Local imports
from .embeddings import get_embedding_model 

# Configuration
CHUNK_SIZE = 1024
CHUNK_OVERLAP = 48
PERSIST_DIRECTORY = "./data/chroma_db"

Path(PERSIST_DIRECTORY).mkdir(parents=True, exist_ok=True)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    add_start_index=True,
)

_vector_store = None

def get_vector_store() -> Chroma:
    """Initializes and returns the Chroma vector store instance."""
    global _vector_store
    if _vector_store is None:
        print(f"Loading vector store from: {PERSIST_DIRECTORY}")
        embedding_function = get_embedding_model() # Gets official JinaEmbeddings
        _vector_store = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            embedding_function=embedding_function # Pass the official embedding function
        )
        print("Vector store loaded.")
    return _vector_store

# --- Core Functions ---

def add_document_to_store(doc_id: int, user_id: int, text: str):
    """
    Splits text, creates documents with metadata, and adds them to the vector store
    using the synchronous embedding function provided by LangChain's JinaEmbeddings.
    """
    if not text:
        print(f"Warning: No text provided for doc_id {doc_id}. Skipping vector store addition.")
        return

    print(f"Splitting text for doc_id {doc_id} (User: {user_id})...")
    chunks = text_splitter.split_text(text)
    print(f"Created {len(chunks)} chunks.")

    if not chunks:
        print(f"Warning: No chunks created after splitting for doc_id {doc_id}.")
        return

    langchain_docs = []
    for i, chunk in enumerate(chunks):
        metadata = {
            "doc_id": doc_id,
            "user_id": user_id,
            "chunk_index": i,
            "source": f"doc_{doc_id}_chunk_{i}"
        }
        doc = Document(page_content=chunk, metadata=metadata)
        langchain_docs.append(doc)

    print(f"Adding {len(langchain_docs)} documents to vector store for doc_id {doc_id}...")
    try:
        vector_store = get_vector_store()
        vector_store.add_documents(langchain_docs)
        print(f"Successfully added documents for doc_id {doc_id} to vector store.")
    except Exception as e:
        import traceback
        print(f"ERROR adding documents to vector store for doc_id {doc_id}: {e}")
        print(traceback.format_exc())


def get_retriever(user_id: int, doc_ids: Optional[List[int]] = None, search_k: int = 4) -> Optional[VectorStoreRetriever]:
    """
    Creates retriever filtering by user_id and optionally a list of doc_ids.
    """
    try:
        vector_store = get_vector_store()
        search_kwargs: Dict[str, Any] = {"k": search_k}

        # --- Filter Logic for Multiple doc_ids ---
        filters = [{"user_id": {"$eq": user_id}}] # Always filter by user
        if doc_ids: # If a list of doc_ids is provided
            if len(doc_ids) == 1:
                # Optimize for single doc ID
                filters.append({"doc_id": {"$eq": doc_ids[0]}})
            else:
                # Use $or for multiple doc IDs (or $in if supported reliably)
                or_clauses = [{"doc_id": {"$eq": d_id}} for d_id in doc_ids]
                filters.append({"$or": or_clauses})

        # Combine all filters with $and
        where_filter = {"$and": filters} if len(filters) > 1 else filters[0]

        search_kwargs["filter"] = where_filter

        print(f"Creating retriever with search_kwargs: {search_kwargs}")
        return vector_store.as_retriever(search_kwargs=search_kwargs)

    except Exception as e:
        print(f"Error creating retriever: {e}")
        return None


def delete_documents_from_store(doc_id: int, user_id: int):
    """Deletes documents associated with a specific doc_id and user_id."""
    print(f"Attempting to delete documents for doc_id {doc_id} (User: {user_id})...")
    try:
        vector_store = get_vector_store()
        where_filter = {"$and": [{"user_id": {"$eq": user_id}}, {"doc_id": {"$eq": doc_id}}]}
        response = vector_store.get(where=where_filter)
        ids_to_delete = response.get('ids')
        if ids_to_delete:
            print(f"Found {len(ids_to_delete)} vector IDs to delete.")
            vector_store.delete(ids=ids_to_delete)
            print(f"Successfully deleted vectors for doc_id {doc_id}.")
        else:
            print(f"No vectors found matching doc_id {doc_id} / user_id {user_id} for deletion.")
    except Exception as e:
        print(f"ERROR deleting documents from vector store for doc_id {doc_id}: {e}")


if __name__ == '__main__':
    print("\n--- Testing Vector Store (Sync Add) ---")
    try:
        embedding_model = get_embedding_model() # Initialize Jina via LangChain
    except ValueError as e:
        print(f"Configuration Error: {e}")
        exit()

    test_doc_id = 998 # Use different ID to avoid conflicts if old data persists
    test_user_id = 102
    test_text_content = "Testing sync add. Sentence one about dogs. Sentence two about cats."
    print(f"\nTesting adding doc_id={test_doc_id}, user_id={test_user_id}")
    # Call the synchronous function directly
    add_document_to_store(doc_id=test_doc_id, user_id=test_user_id, text=test_text_content)

    print(f"\nTesting retrieval for user_id={test_user_id}, doc_id={test_doc_id}")
    retriever = get_retriever(user_id=test_user_id, doc_id=[test_doc_id])
    if retriever:
        query = "What animals are mentioned?"
        try:
            print(f"Invoking SYNC retriever for query: '{query}'")
            results = retriever.invoke(query) # Use synchronous invoke
            print(f"Query: '{query}'")
            print(f"Retrieved {len(results)} documents:")
            for i, doc in enumerate(results):
                print(f"  Result {i+1}: Metadata={doc.metadata}, Content='{doc.page_content[:100]}...'")
        except Exception as e:
             import traceback
             print(f"ERROR during SYNC retriever invocation: {e}")
             print(traceback.format_exc())
    else:
        print("Failed to create retriever.")

    # Test deletion
    print(f"\nTesting deletion for doc_id={test_doc_id}, user_id={test_user_id}")
    delete_documents_from_store(doc_id=test_doc_id, user_id=test_user_id)

    # Verify deletion
    print(f"\nVerifying deletion by retrieving again...")
    retriever_after_delete = get_retriever(user_id=test_user_id, doc_id=[test_doc_id])
    if retriever_after_delete:
        try:
            results_after_delete = retriever_after_delete.invoke(query) # Use synchronous invoke
            print(f"Retrieved {len(results_after_delete)} documents after deletion (expected 0).")
        except Exception as e:
            print(f"ERROR during SYNC retriever invocation after delete: {e}")
    else:
         print("Failed to create retriever after deletion.")
