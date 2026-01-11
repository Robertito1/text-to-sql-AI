# SQL Query AI Assistant

A natural language to SQL query assistant with a React frontend and FastAPI backend. Ask questions about your database in plain English and get results with visualizations.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  React Frontend │────▶│  FastAPI Backend│────▶│    Supabase     │
│  (Vercel)       │     │  (Render)       │     │   PostgreSQL    │
│                 │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │                 │
                        │    Groq API     │
                        │  (LLM - Llama)  │
                        │                 │
                        └─────────────────┘
```

### Components

- **Frontend**: React + TypeScript + TailwindCSS hosted on Netlify
- **Backend**: FastAPI + LangChain + RAG (ChromaDB + Cohere Embeddings) hosted on Render
- **Database**: Supabase PostgreSQL (free tier)
- **LLM**: Groq API with Llama 3.3 70B (free, very fast)
- **Embeddings**: Cohere API (free tier)

### How It Works

1. User asks a question in natural language
2. Question is classified to ensure it's database-related
3. Backend uses RAG (Cohere embeddings + ChromaDB) to retrieve relevant schema documentation
4. Conversation history is included for follow-up questions
5. LLM generates PostgreSQL query based on schema context
6. Query is validated for safety (read-only)
7. Query executes against Supabase PostgreSQL
8. Results are returned with auto-generated charts and natural language summary

## Project Structure

```
text-to-sql-AI/
├── server/                 # Backend (FastAPI + LangChain)
│   ├── app/
│   │   ├── agent.py       # SQL generation and execution with RAG
│   │   ├── db.py          # Database connection (PostgreSQL/SQL Server)
│   │   ├── llm.py         # Groq LLM configuration
│   │   ├── main.py        # FastAPI endpoints
│   │   ├── models.py      # Pydantic models
│   │   ├── safe_sql.py    # SQL safety checks
│   │   └── schema_docs.py # Schema documentation for RAG
│   ├── chroma_db/         # Vector store for RAG embeddings
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/              # Frontend (React + Vite + TailwindCSS)
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── App.tsx        # Main app component
│   │   ├── api.ts         # API client
│   │   └── types.ts       # TypeScript types
│   └── package.json
├── populate_database.py         # Script to populate SQL Server test data
└── populate_database_postgres.py # Script to populate PostgreSQL test data
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- Database: PostgreSQL (Supabase) or SQL Server
- Groq API key
- Cohere API key

## Setup

### 1. Backend Setup

```bash
cd server

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment variables in .env:
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
COHERE_API_KEY=cohere-api-key

# For PostgreSQL (Supabase):
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

# For SQL Server (optional):
ODBC_STR=Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=YourDB;UID=user;PWD=password;
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### 3. Populate Test Data (Optional)

```bash
# For PostgreSQL (Supabase)
python populate_database_postgres.py

# For SQL Server
python populate_database.py
```

## Running the Application

### Start the Backend

```bash
cd server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start the Frontend

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Running with Docker (Local Development)

Docker Compose is configured for local development with SQL Server. To use Supabase PostgreSQL instead, set the `DATABASE_URL` environment variable.

### Prerequisites
- Docker and Docker Compose installed
- Create a `.env` file in the project root with your API keys:
  ```
  GROQ_API_KEY=your_groq_api_key
  COHERE_API_KEY=your_cohere_api_key
  ```

### Option 1: With Local SQL Server
```bash
# Start all services (SQL Server + API + Frontend)
docker-compose up --build

# Access:
# - Frontend: http://localhost:80
# - API: http://localhost:8000
# - SQL Server: localhost:1433
```

### Option 2: With Supabase PostgreSQL
```bash
# Add DATABASE_URL to your .env file
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

# Start only API and Frontend (skip local SQL Server)
docker-compose up --build api frontend
```

### Development Mode (Hot Reload)
```bash
# Uses docker-compose.override.yml for hot reloading
docker-compose -f docker-compose.yml -f docker-compose.override.yml up

# Access:
# - Frontend: http://localhost:5173
# - API: http://localhost:8000
```

## Features

- **Natural Language Queries**: Ask questions in plain English
- **Conversation Memory**: Follow-up questions understand context from previous Q&A
- **Question Validation**: Off-topic questions are politely redirected
- **SQL Generation**: Automatically generates safe, read-only SQL queries
- **Data Visualization**: Charts (bar, line, pie) based on query results
- **Data Tables**: View raw query results in a formatted table
- **SQL Display**: See the generated SQL with copy functionality
- **RAG-Enhanced**: Uses Cohere embeddings + ChromaDB for schema context

## Example Questions

- "How many customers do we have in each country?"
- "Show monthly revenue for the last 6 months"
- "Who are the top 10 customers by total spending?"
- "What percentage of orders are cancelled?"
- "What is the average order amount by status?"

## API Endpoints

- `GET /health` - Health check
- `POST /ask` - Submit a natural language question

### Request Format

```json
{
  "question": "How many customers are there?"
}
```

### Response Format

```json
{
  "success": true,
  "summary": "There are 1000 customers.",
  "sql": "SELECT COUNT(*) FROM Customers",
  "data": [{"count": 1000}],
  "chart": {
    "type": "bar",
    "x_key": "category",
    "y_key": "value",
    "title": "Query Results"
  },
  "error": null
}
```

## Tech Stack

### Backend
- FastAPI
- LangChain
- Groq API (LLM - llama-3.3-70b-versatile)
- Cohere API
- ChromaDB (vector store)
- SQLAlchemy + psycopg2 (PostgreSQL) / pyodbc (SQL Server)

### Frontend
- React 18
- TypeScript
- Vite
- TailwindCSS
- Recharts
- Lucide Icons

## Deployment

- **Frontend**: Netlify
- **Backend**: Render
- **Database**: Supabase PostgreSQL
- **LLM**: Groq API
- **Embeddings**: Cohere API

## Testing

### Backend Tests
```bash
cd server
pip install pytest pytest-asyncio httpx
python -m pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm install
npm run test
```

Tests run automatically on every push via GitHub Actions CI.
