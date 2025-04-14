# ml_core/qa_chain.py
from typing import Optional, List, Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langchain_core.documents import Document

from .vector_store import get_retriever
from app.core.config import settings 
from app.db.models import ChatSession
from app.db.database import async_session_local # Need session factory
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# --- LLM Initialization ---
try:
    llm = ChatGroq(
        groq_api_key=settings.GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile",
        temperature=0.1 # Lower temperature for more factual/less creative responses
    )
    print("Groq LLM initialized successfully.")
except Exception as e:
    print(f"ERROR initializing Groq LLM: {e}")
    print("Ensure GROQ_API_KEY is set correctly in your .env file.")
    llm = None # Set to None to indicate failure

# --- Prompt Template ---
# Define a template that instructs the LLM how to use the context
system_prompt ="""
    You are a highly knowledgeable and reliable legal assistant.
    You specialize in understanding and summarizing legal documents and answering legal questions.
    Your behavior guidelines:
    You only respond to legal topics, including document, legal procedures, terms, and regulations.
    If a user uploads a document and asks questions about it—even if the word 'legal' is not in the question—assume the document is legal and provide a clear, concise answer of its legal content.
    If the context contains a legal document, respond to relevant questions even if the query doesn't contain an explicit legal keyword.
    If the context is clearly non-legal and the question is general, respond:
    "I'm designed to answer legal questions or assist with legal documents. Please ask something related to law."
    If you cannot answer due to lack of context, respond:
    "I don't have enough information in the provided legal context to answer that."
    Always prioritize legal accuracy and relevance. Do not fabricate information.
    """

chat_template = """
        Context:
        {context}

        Question: {question}

        Answer:
    """

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", chat_template)
])


# --- Output Parser ---
output_parser = StrOutputParser()

# --- Helper Function to Format Documents ---
def format_docs(docs: List[Document]) -> str:
    """Concatenates page content of retrieved documents."""
    if not docs:
        return "No relevant context found."
    return "\n\n".join(doc.page_content for doc in docs)

# --- RAG Chain Definition (using LCEL) ---
def get_rag_chain(user_id: int, doc_ids: Optional[List[int]] = None): # Accept list of doc_ids
    """Creates the complete RAG chain based on user and document IDs."""
    # Pass list of doc_ids to get_retriever
    retriever = get_retriever(user_id=user_id, doc_ids=doc_ids)
    if retriever is None: raise ValueError("Failed to create retriever.")
    if llm is None: raise ValueError("LLM not initialized.")

    rag_chain_from_docs = ( RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"]))) | prompt | llm | output_parser )
    rag_chain_with_source = RunnableParallel( {"context": retriever, "question": RunnablePassthrough()} ).assign(answer=rag_chain_from_docs)
    return rag_chain_with_source

# --- Main Function to Get Response ---
async def get_rag_response(query: str, user_id: int, session_id: int) -> Dict[str, Any]:
    """
    Fetches doc_ids for the session, invokes RAG chain, returns result.
    """
    print(f"Invoking RAG for user {user_id}, session {session_id}, query: '{query[:50]}...'")
    doc_ids: List[int] = []

    # Fetch associated document IDs from the database
    async with async_session_local() as db_session:
        session_query = (
            select(ChatSession)
            .options(selectinload(ChatSession.documents)) # Eager load documents
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        result = await db_session.execute(session_query)
        session = result.scalars().first()
        if session:
            doc_ids = [doc.id for doc in session.documents]
            print(f"Found {len(doc_ids)} documents linked to session {session_id}: {doc_ids}")
        else:
            # Should have been caught by API layer, but handle defensively
            print(f"Warning: Session {session_id} not found for user {user_id} in RAG function.")
            # Proceed with no specific doc IDs (retriever will only filter by user)

    try:
        # Pass the fetched doc_ids to get_rag_chain
        chain = get_rag_chain(user_id=user_id, doc_ids=doc_ids if doc_ids else None)
        result = await chain.ainvoke(query)
        if not isinstance(result, dict):
            print(f"Warning: RAG chain returned unexpected type: {type(result)}")
            return {"answer": "Error processing response.", "context": []}
        print(f"RAG chain invocation successful. Answer: '{result.get('answer', '')[:100]}...'")
        context_docs = result.get("context", [])
        if not isinstance(context_docs, list) or not all(isinstance(doc, Document) for doc in context_docs):
            print(f"Warning: RAG chain context is not a list of Documents: {type(context_docs)}")
            result["context"] = []
        return result

    except ValueError as ve:
        print(f"Error getting RAG response: {ve}")
        return {"answer": f"Error: {ve}", "context": []}
    except Exception as e:
        import traceback
        print(f"Error invoking RAG chain: {e}")
        print(traceback.format_exc())
        return {"answer": "Sorry, an error occurred processing your request.", "context": []}