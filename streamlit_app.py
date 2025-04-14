# streamlit_app.py
import streamlit as st
import httpx
from typing import Optional, List, Dict, Any
import mimetypes
from pathlib import Path
import asyncio

try:
    from app.core.config import settings
    BACKEND_URL = settings.BACKEND_API_BASE_URL
except ImportError:
    # Fallback if running streamlit from a different context might need direct URL
    print("Warning: Could not import settings. Using default backend URL.")
    BACKEND_URL = "http://localhost:8000"


# --- API Client Functions ---

async def api_login(username: str, password: str) -> Optional[str]:
    """Attempts to log in via API and returns the auth token or None."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/auth/token",
                data={"username": username, "password": password}
            )
            response.raise_for_status() # Raise exceptions for 4xx/5xx
            return response.json().get("access_token")
        except httpx.HTTPStatusError as e:
            st.error(f"Login failed: {e.response.status_code} - {e.response.json().get('detail', 'Unknown error')}")
            return None
        except Exception as e:
            st.error(f"An error occurred during login: {e}")
            return None

async def api_get_documents(token: str) -> List[Dict]:
    """Fetches user documents from the API."""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BACKEND_URL}/documents/", headers=headers)
            response.raise_for_status()
            return response.json().get("documents", [])
        except Exception as e:
            st.error(f"Failed to fetch documents: {e}")
            return []

async def api_upload_document(token: str, uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> bool:
    """Uploads a document file to the backend API."""
    headers = {"Authorization": f"Bearer {token}"}
    file_content = uploaded_file.getvalue()
    file_name = uploaded_file.name
    content_type, _ = mimetypes.guess_type(file_name)
    content_type = content_type or "application/octet-stream"
    api_files = {'file': (file_name, file_content, content_type)}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BACKEND_URL}/documents/upload", files=api_files, headers=headers, timeout=60.0)
            response.raise_for_status()
            st.success(f"Successfully uploaded `{file_name}` (Doc ID: {response.json().get('doc_id')}). Processing in background.")
            return True
        except httpx.HTTPStatusError as e:
            st.error(f"Upload Failed: {e.response.status_code} - {e.response.json().get('detail', e.response.text)}")
            return False
        except Exception as e:
            st.error(f"Upload Error: {e}")
            return False
        
async def api_delete_document(token: str, doc_id: int) -> bool:
    """Deletes a document via the API."""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{BACKEND_URL}/documents/{doc_id}", headers=headers, timeout=30.0)
            response.raise_for_status()
            st.success(f"Document ID {doc_id} deletion initiated.")
            return True
        except httpx.HTTPStatusError as e:
            st.error(f"Deletion Failed: {e.response.status_code} - {e.response.json().get('detail', e.response.text)}")
            return False
        except Exception as e:
            st.error(f"Deletion Error: {e}")
            return False

async def api_get_chat_history(token: str, session_id: int) -> List[Dict]:
    """Fetches chat history from the API for a specific session."""
    headers = {"Authorization": f"Bearer {token}"}
    endpoint = f"{BACKEND_URL}/chat/history/{session_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(endpoint, headers=headers)
            response.raise_for_status()
            return response.json().get("history", [])
        except Exception as e:
            st.error(f"Failed to fetch chat history for session {session_id}: {e}")
            return []

async def api_post_chat_message(token: str, query: str, session_id: int) -> Optional[str]:
    """Sends a chat message to the API for a specific session."""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"query": query, "session_id": session_id}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BACKEND_URL}/chat/", json=payload, headers=headers, timeout=120.0)
            response.raise_for_status()
            return response.json().get("answer")
        except httpx.HTTPStatusError as e:
            st.error(f"Chat API Error: {e.response.status_code} - {e.response.json().get('detail', e.response.text)}")
            return "Sorry, an API error occurred."
        except Exception as e:
            st.error(f"Error sending message: {e}")
            return "Sorry, an unexpected error occurred."
        
async def api_get_sessions(token: str) -> List[Dict]:
    """Fetches user's chat sessions from the API."""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BACKEND_URL}/sessions/", headers=headers)
            response.raise_for_status()
            return response.json().get("sessions", [])
        except Exception as e:
            st.error(f"Failed to fetch sessions: {e}")
            return []

async def api_create_session(token: str, name: Optional[str] = None, doc_ids: Optional[List[int]] = None) -> Optional[Dict]:
    """Creates a new chat session via the API."""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"session_name": name or "New Chat", "document_ids": doc_ids or []}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BACKEND_URL}/sessions/", json=payload, headers=headers)
            response.raise_for_status()
            st.success(f"Created new session: {response.json().get('session_name')}")
            return response.json() # Return the created session data
        except httpx.HTTPStatusError as e:
            st.error(f"Failed to create session: {e.response.status_code} - {e.response.json().get('detail', e.response.text)}")
            return None
        except Exception as e:
            st.error(f"Error creating session: {e}")
            return None

async def api_delete_session(token: str, session_id: int) -> bool:
    """Deletes a chat session via the API."""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{BACKEND_URL}/sessions/{session_id}", headers=headers)
            response.raise_for_status()
            st.success(f"Session ID {session_id} deleted.")
            return True
        except httpx.HTTPStatusError as e:
            st.error(f"Failed to delete session: {e.response.status_code} - {e.response.json().get('detail', e.response.text)}")
            return False
        except Exception as e:
            st.error(f"Error deleting session: {e}")
            return False

# --- Streamlit App Logic ---

st.set_page_config(page_title="Legal AI Chatbot", layout="wide")
st.title("⚖️ Legal AI Chatbot")

# Initialize session state variables
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.sessions = [] # List of session dicts
    st.session_state.documents = [] # List of document dicts
    st.session_state.active_session_id = None # ID of the currently active session
    st.session_state.active_session_name = "No Session Selected"
    st.session_state.messages = [] # Chat messages for the active session


# --- Login Screen ---
if not st.session_state.authenticated:
    # ... (login logic remains the same) ...
    st.subheader("Login")
    st.info("Register via backend API docs at /docs#/Authentication/register_user_auth_register_post first.")
    login_username = st.text_input("Username")
    login_password = st.text_input("Password", type="password")
    if st.button("Login"):
        if login_username and login_password:
            with st.spinner("Logging in..."):
                token = asyncio.run(api_login(login_username, login_password))
            if token:
                st.session_state.authenticated = True
                st.session_state.token = token
                st.session_state.username = login_username
                # Initialize empty lists for documents/sessions on successful login
                st.session_state.documents = []
                st.session_state.sessions = []
                st.session_state.active_session_id = None
                st.session_state.active_session_name = "No Session Selected"
                st.session_state.messages = []
                st.rerun()
        else:
            st.warning("Please enter both username and password.")


# --- Main Application UI ---
else:
    if not st.session_state.documents: # Fetch documents if list is empty
        with st.spinner("Loading documents..."):
            st.session_state.documents = asyncio.run(api_get_documents(st.session_state.token))

    if not st.session_state.sessions: # Fetch sessions if list is empty
        with st.spinner("Loading chat sessions..."):
            st.session_state.sessions = asyncio.run(api_get_sessions(st.session_state.token))
        

    # --- Sidebar ---
    with st.sidebar:
        st.subheader(f"Welcome, {st.session_state.username}!")
        st.divider()

        # --- Chat Session Management ---
        st.subheader("Chat Sessions")

        # Button to create a new session
        if st.button("➕ New Chat Session"):
            # Optional: Allow selecting documents for the new session
            available_docs = {f"{doc['filename']} (ID: {doc['id']})": doc['id'] for doc in st.session_state.documents}
            selected_doc_labels = []
            if available_docs:
                 selected_doc_labels = st.multiselect("Link documents to new session (optional):", options=available_docs.keys())
            doc_ids_to_link = [available_docs[label] for label in selected_doc_labels if label in available_docs]

            session_name_input = st.text_input("New session name (optional):", value="New Chat")

            with st.spinner("Creating new session..."):
                new_session_data = asyncio.run(api_create_session(st.session_state.token, session_name_input, doc_ids_to_link ))
            if new_session_data:
                # Refresh session list and activate the new one
                st.session_state.sessions = asyncio.run(api_get_sessions(st.session_state.token))
                st.session_state.active_session_id = new_session_data['id']
                st.session_state.active_session_name = new_session_data['session_name']
                st.session_state.messages = [] # Clear messages for new session
                st.rerun()

        st.write("Select Session:")
        # Display existing sessions with select/delete buttons
        for session in st.session_state.sessions:
            cols = st.columns([0.7, 0.15, 0.15])
            with cols[0]:
                # Button to activate session
                is_active = (session['id'] == st.session_state.active_session_id)
                button_type = "primary" if is_active else "secondary"
                label = session['session_name'] or f"Session {session['id']}"
                if st.button(label, key=f"session_{session['id']}", type=button_type, use_container_width=True):
                    if not is_active: # Only switch if not already active
                        st.session_state.active_session_id = session['id']
                        st.session_state.active_session_name = label
                        st.session_state.messages = [] # Clear messages
                        # History will be loaded in the main area
                        st.rerun()
            with cols[1]:
                # Button to delete session
                 if st.button("🗑️", key=f"del_session_{session['id']}", help=f"Delete '{label}'"):
                     with st.spinner(f"Deleting session {session['id']}..."):
                         deleted = asyncio.run(api_delete_session(st.session_state.token, session['id']))
                     if deleted:
                         # If deleting the active session, reset active session state
                         if session['id'] == st.session_state.active_session_id:
                             st.session_state.active_session_id = None
                             st.session_state.active_session_name = "No Session Selected"
                             st.session_state.messages = []
                         # Refresh session list
                         st.session_state.sessions = asyncio.run(api_get_sessions(st.session_state.token))
                         st.rerun()


        st.divider()

        # --- Document Management ---
        st.subheader("Manage Documents")
        # Upload section
        uploaded_file = st.file_uploader(
            "Upload New Document (PDF, DOCX, etc.)",
            type=["pdf", "docx", "png", "jpg", "jpeg"],
            accept_multiple_files=False,
            key="doc_uploader" # Add a key
        )
        if uploaded_file is not None:
            if st.button(f"Process `{uploaded_file.name}`", key=f"upload_{uploaded_file.file_id}"):
                with st.spinner(f"Uploading {uploaded_file.name}..."):
                    success = asyncio.run(api_upload_document(st.session_state.token, uploaded_file))
                if success:
                    # Refresh document list
                    st.session_state.documents = asyncio.run(api_get_documents(st.session_state.token))
                    st.rerun()

        # List and Delete documents
        st.write("Uploaded Documents:")
        if not st.session_state.documents:
            st.caption("No documents uploaded yet.")
        else:
            for doc in st.session_state.documents:
                doc_cols = st.columns([0.85, 0.15])
                with doc_cols[0]:
                    st.text(f"- {doc['filename']} (ID: {doc['id']})")
                with doc_cols[1]:
                    if st.button("🗑️", key=f"del_doc_{doc['id']}", help=f"Delete {doc['filename']}"):
                        with st.spinner(f"Deleting document {doc['id']}..."):
                            deleted = asyncio.run(api_delete_document(st.session_state.token, doc['id']))
                        if deleted:
                            # Refresh document list
                            st.session_state.documents = asyncio.run(api_get_documents(st.session_state.token))
                            # If this doc was part of the active session, the RAG will just get less context next time
                            # Might want to refresh sessions too if session names depended on docs
                            st.rerun()

        # Logout Button
        st.divider()
        if st.button("Logout"):
            # Clear session state and rerun
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # --- Main Chat Area ---
    st.subheader(f"Chat: {st.session_state.active_session_name}")

    # Check if a session is active
    if st.session_state.active_session_id is None:
        st.info("Please select a chat session or create a new one from the sidebar.")
    else:
        # Load history if messages are empty for the active session
        if not st.session_state.messages:
            with st.spinner("Loading chat history..."):
                history = asyncio.run(api_get_chat_history(st.session_state.token, st.session_state.active_session_id))
            for item in history:
                st.session_state.messages.append({"role": "user", "content": item["message"]})
                st.session_state.messages.append({"role": "assistant", "content": item["response"]})
            # Rerun only if history was actually loaded to prevent loops
            if history:
                st.rerun()

        # Display messages for the active session
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Handle new chat input for the active session
        if prompt := st.chat_input("Ask a legal question..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get response from API for the active session
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("Thinking...")
                answer = asyncio.run(
                    api_post_chat_message(
                        st.session_state.token,
                        prompt,
                        st.session_state.active_session_id # Pass active session ID
                    )
                )
                message_placeholder.markdown(answer or "Sorry, no response received.")
                if answer:
                    st.session_state.messages.append({"role": "assistant", "content": answer})