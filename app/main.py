# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routers import auth # Import other routers later (documents, chat)
from app.db.database import init_db, engine
from app.core.config import settings # Import settings if needed directly

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Actions on startup
    print("Application startup...")
    # Connect to DB (though sessions are managed per-request, engine connection pooling happens here)
    # Create tables if they don't exist
    await init_db()
    yield
    # Actions on shutdown
    print("Application shutdown...")
    # Properly close the engine connection pool
    await engine.dispose()


app = FastAPI(
    title="Legal AI Chatbot API",
    description="API for the Legal AI Chatbot application.",
    version="0.1.0",
    lifespan=lifespan # Use lifespan context manager
)

# Include API routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# Add other routers here later:
# app.include_router(documents.router, prefix="/documents", tags=["Documents"])
# app.include_router(chat.router, prefix="/chat", tags=["Chat"])


@app.get("/health", tags=["Health Check"])
async def health_check():
    """Basic health check endpoint."""
    # You could add checks like DB connectivity here
    return {"status": "ok"}

# Optional: If you need to run init_db manually or via a separate script
# import asyncio
# if __name__ == "__main__":
#     asyncio.run(init_db())

