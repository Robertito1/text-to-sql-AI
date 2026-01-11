from dotenv import load_dotenv
load_dotenv()

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import QueryRequest, QueryResponse
from .agent import answer_question
from .db import init_database, close_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events."""
    # Startup
    logger.info("Initializing database connection pool...")
    try:
        init_database()
        logger.info("Database connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Closing database connections...")
    close_database()
    logger.info("Application shutdown complete")

app = FastAPI(
    title="SQL Query AI Assistant",
    description="Natural language to SQL query assistant with RAG",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
     allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://text-to-sql-ai.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "sql-query-ai-assistant"}

@app.post("/ask", response_model=QueryResponse)
async def ask_sql_question(req: QueryRequest):
    """
    Ask a natural language question about your SQL database.
    
    The system will:
    1. Retrieve relevant schema context using RAG
    2. Generate a safe, read-only SQL query
    3. Execute the query
    4. Return structured data with summary, chart config, and raw data
    """
    try:
        logger.info(f"Processing question: {req.question}")
        history = req.history if req.history else []
        response = answer_question(req.question, history)
        logger.info("Question answered successfully")
        return response
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        return QueryResponse(
            success=False,
            summary=f"An error occurred: {str(e)}",
            error=str(e)
        )
