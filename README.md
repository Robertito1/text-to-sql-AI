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
└── populate_database.py   # Script to populate test data
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- SQL Server database
- Ollama with a model installed (e.g., `llama3.2`)

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

# Configure environment variables
# Edit .env file with your database connection string:
# ODBC_STR=Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=YourDB;UID=user;PWD=password;
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### 3. Populate Test Data (Optional)

```bash
# From project root
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
  "data": [{"col_0": 1000}],
  "chart": {
    "type": "bar",
    "x_key": "col_0",
    "y_key": "col_1",
    "title": "Query Results"
  },
  "error": null
}
```

## Tech Stack

### Backend
- FastAPI
- LangChain
- Ollama (local LLM)
- ChromaDB (vector store)
- SQLAlchemy + pyodbc

### Frontend
- React 18
- TypeScript
- Vite
- TailwindCSS
- Recharts
- Lucide Icons
