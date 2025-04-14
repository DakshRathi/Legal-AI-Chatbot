# Legal AI Chatbot

## Overview

This project implements the Legal AI Chatbot, a specialized ML-powered platform designed to deliver domain-specific legal assistance via natural conversation, based on the provided Product Specification. It integrates document analysis (OCR, NER), multi-document context retrieval using Retrieval-Augmented Generation (RAG), and session-based chat interaction.

The application consists of a FastAPI backend handling API requests, ML processing, and database interactions, and a Streamlit frontend providing the user interface for login, document management, session management, and chat.

## Features Implemented

*   **User Authentication:** Secure JWT-based user login via FastAPI backend. (Registration currently via API docs).
*   **Document Upload:** Upload legal documents (PDF, DOCX, PNG, JPG/JPEG) via the Streamlit interface.
*   **Document Processing:**
    *   **OCR:** Extracts text from scanned PDFs and images using Pytesseract (requires Tesseract installation).
    *   **Text Extraction:** Parses text from digital PDFs (`pypdf`) and Word documents (`python-docx`).
    *   **Named Entity Recognition (NER):** Identifies Dates, Organizations, and Persons using SpaCy (`en_core_web_lg`). NER results are stored as metadata.
*   **Session-Based Chat:**
    *   Create, select, and delete distinct chat sessions.
    *   Link one or more uploaded documents to a specific chat session.
    *   Chat history is maintained per session.
*   **Multi-Document RAG Q&A:**
    *   When chatting within a session, questions are answered based on the context retrieved from *all* documents linked to that session.
    *   Uses LangChain for orchestration, ChromaDB for vector storage, Jina AI Embeddings API for generating text embeddings, and the Groq API (Mixtral model) for language generation.
*   **Document & Session Management:**
    *   List uploaded documents.
    *   Delete uploaded documents (removes from database and vector store).
    *   List chat sessions.
    *   Delete chat sessions (including associated messages).
*   **Streamlit Frontend:** Interactive web interface for all user-facing features.

## Technology Stack

*   **Backend Framework:** FastAPI
*   **Frontend Framework:** Streamlit
*   **LLM Orchestration:** LangChain (`langchain-core`, `langchain-text-splitters`, `langchain-chroma`, `langchain-groq`)
*   **LLM Provider:** Groq API
*   **Embeddings:** Jina AI Embeddings API (via `langchain-community`)
*   **Vector Store:** ChromaDB (local persistence)
*   **NER:** SpaCy (`en_core_web_lg`)
*   **Database ORM:** SQLAlchemy (with `asyncio` support)
*   **Database:** SQLite
*   **Authentication:** JWT (`python-jose`, `passlib`)
*   **OCR:** Pytesseract (+ system Tesseract installation)
*   **Document Parsing:** `pypdf`, `python-docx`, `Pillow`
*   **API Client (Streamlit):** `httpx`
*   **Configuration:** `pydantic-settings`, `.env` file


## Architecture Overview

1.  **Streamlit Frontend (`streamlit_app.py`):**
    *   Handles user login via API call to backend.
    *   Provides UI for uploading/deleting documents, creating/selecting/deleting chat sessions.
    *   Sends user chat messages to the backend API (including active session ID).
    *   Displays chat history and responses received from the backend.
2.  **FastAPI Backend (`app/`):**
    *   **API Routers (`app/routers/`):** Defines endpoints for `/auth`, `/documents`, `/sessions`, `/chat`. Handles request validation and authentication.
    *   **Database (`app/db/`):** Manages user, document, session, and message data in SQLite using SQLAlchemy.
    *   **ML Core (`ml_core/`):**
        *   `document_processor.py`: Handles OCR, text extraction, and SpaCy NER.
        *   `embeddings.py`: Configures the Jina embeddings model (via LangChain).
        *   `vector_store.py`: Manages adding/deleting/retrieving document chunks and embeddings from ChromaDB, filtering by user and document IDs.
        *   `qa_chain.py`: Implements the RAG logic using LangChain, fetching relevant document IDs for the current session, retrieving context from `vector_store`, formatting prompts, calling the Groq LLM, and returning the answer.
3.  **Data Stores:**
    *   **SQLite (`data/sql_app.db`):** Stores structured data (users, documents metadata, sessions, messages).
    *   **ChromaDB (`data/chroma_db/`):** Stores document chunk embeddings for similarity search.

## Prerequisites

*   **Python:** Version 3.10 or higher recommended.
*   **Tesseract OCR:** Must be installed on your system and accessible in the PATH.
    *   **macOS:** `brew install tesseract`
    *   **Debian/Ubuntu:** `sudo apt-get update && sudo apt-get install tesseract-ocr`
    *   **Windows:** Download installer from [UB Mannheim Tesseract GitHub](https://github.com/UB-Mannheim/tesseract/wiki). Ensure the installation directory is added to your system's PATH.
*   **Virtual Environment:** Recommended to avoid dependency conflicts (e.g., using `venv`).

## Setup Instructions

1.  **Clone the Repository:**
    ```
    git clone https://github.com/DakshRathi/Legal-AI-Chatbot.git
    cd legal-ai-chatbot
    ```

2.  **Create and Activate Virtual Environment**

3.  **Install Dependencies:**
    ```
    pip install -r requirements.txt
    ```

4.  **Download SpaCy Model:**
    ```
    python -m spacy download en_core_web_lg
    ```

5.  **Configure Environment Variables:**
    Create a `.env` file in the project root (`legal-ai-chatbot/.env`) with the following content, replacing placeholder values with your actual credentials/settings:
    ```
    # .env
    GROQ_API_KEY="your_groq_api_key"          # Get from console.groq.com
    JINA_API_KEY="your_jina_api_key"          # Get from jina.ai/embeddings
    SECRET_KEY="generate_a_strong_random_secret_key" # Used for JWT tokens
    ALGORITHM="HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    DATABASE_URL="sqlite+aiosqlite:///./data/sql_app.db" # Default path for SQLite DB
    BACKEND_API_BASE_URL="http://localhost:8000"       # URL for the FastAPI backend
    ```
    *   Generate a strong `SECRET_KEY` (e.g., using `openssl rand -hex 32`).

6.  **Database Initialization:** The database tables will be created automatically when the FastAPI backend starts for the first time (via the `init_db` function called during application startup).

## Running the Application

You need to run the backend and frontend separately.

1.  **Run the FastAPI Backend:**
    Open a terminal, activate your virtual environment, and run:
    ```
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    Keep this terminal running. Check for any startup errors.

2.  **Run the Streamlit Frontend:**
    Open a *second* terminal, activate the *same* virtual environment, and run:
    ```
    streamlit run streamlit_app.py
    ```
    Streamlit will provide a URL (usually `http://localhost:8501`) to open in your web browser.

## Usage Guide

1.  **Register (First Time Only):** Since the Streamlit app doesn't have a registration form, you need to register a user directly via the backend API documentation:
    *   Navigate to `http://localhost:8000/docs` in your browser.
    *   Find the `Authentication` section and the `/auth/register` endpoint.
    *   Use "Try it out" to create a user with a username, email, and password.
2.  **Login:** Open the Streamlit application URL (e.g., `http://localhost:8501`). Enter the username and password you registered.

3.  **Sidebar:**
    *   **Chat Sessions:**
        *   Click "➕ New Chat Session" to start a new chat. You can optionally select uploaded documents to link to this session for context.
        *   Select an existing session from the list to activate it and load its history.
        *   Click the "🗑️" button next to a session to delete it.
    *   **Manage Documents:**
        *   Click "Browse files" under "Upload New Document" to select and upload a supported document (PDF, DOCX, PNG, JPG). Click "Process..." to start the upload and background processing.
        *   View the list of previously uploaded documents.
        *   Click the "🗑️" button next to a document to delete it.
    *   **Logout:** Click the "Logout" button.
4.  **Chatting:**
    *   Ensure a chat session is selected in the sidebar. The current session name is displayed above the chat area.
    *   Type your question into the input box at the bottom ("Ask a legal question...") and press Enter.
    *   The chatbot will respond based on the general LLM knowledge or, if documents are linked to the active session, based on the context retrieved from those documents via the RAG pipeline.


## Limitations & Future Work

*   NER is currently limited to basic types (Date, Org, Person) via SpaCy's default model.
*   No domain-specific fine-tuning of LLM or NER models implemented.
*   Semantic search across a corpus of external laws is not implemented.
*   UI is functional via Streamlit; more advanced UI features (animations, etc.) are not included.
*   Error handling can be further improved.
*   Deployment setup for production is not included.
*   Comprehensive test suite is needed.