# SQL Query AI Assistant

A natural language to SQL query assistant with a React frontend and FastAPI backend. Ask questions about your database in plain English and get results with visualizations.

## Project Structure

```
text-to-sql-AI/
├── server/                 # Backend (FastAPI + LangChain)
│   ├── app/
│   │   ├── agent.py       # SQL generation and execution
│   │   ├── db.py          # Database connection
│   │   ├── llm.py         # LLM configuration
│   │   ├── main.py        # FastAPI endpoints
│   │   ├── models.py      # Pydantic models
│   │   ├── safe_sql.py    # SQL safety checks
│   │   └── schema_docs.py # Schema documentation
│   ├── chroma_db/         # Vector store for RAG
│   ├── requirements.txt
│   └── .env
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
- Groq API key (free at https://console.groq.com)

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

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# For development with hot reload
docker-compose -f docker-compose.yml -f docker-compose.override.yml up
```

## Features

- **Natural Language Queries**: Ask questions in plain English
- **SQL Generation**: Automatically generates safe, read-only SQL queries
- **Data Visualization**: Charts (bar, line, pie) based on query results
- **Data Tables**: View raw query results in a formatted table
- **SQL Display**: See the generated SQL with copy functionality
- **RAG-Enhanced**: Uses schema documentation for better query generation

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

- **Frontend**: Vercel or Netlify (free tier)
- **Backend**: Railway or Render (free tier)
- **Database**: Supabase PostgreSQL (free tier)
- **LLM**: Groq API (free, very fast)
