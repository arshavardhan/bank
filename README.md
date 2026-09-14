# 🏦 AI Financial Statement Analysis Agent

A production-ready, deterministic-first AI Financial Statement Analysis Agent in Python. Upload bank statements in **CSV, Excel (.xlsx, .xls), PDF (text or scanned), or Image** formats and ask natural language questions with verified, non-hallucinated analytical answers.

---

## ⚡ Core Principle: Zero LLM Mental Math

> **The LLM never performs financial calculations directly.**  
> Mathematical computations are executed strictly by deterministic Python / SQL analytical tools (`get_total_credits`, `get_merchant_spending`, `get_monthly_summary`, etc.). The LangGraph orchestrator parses user intent, dispatches deterministic tools, audits tool results through a validation layer, and passes the verified calculations to the LLM solely for structured explanation.

---

## 🏛 Architecture

```
User
  │
  ▼
FastAPI (/upload, /ask, /transactions, /summary, /health)
  │
  ▼
Document & Data Extraction (Pandas, PyMuPDF, pdfplumber, pytesseract OCR)
  │
  ▼
Transaction Normalization Layer (Unified Schema: Date, Merchant, Type, Amount, Balance, Category)
  │
  ▼
AI Orchestrator (LangGraph StateGraph)
  ├── Intent Classification & Tool Routing
  ├── Deterministic Python & SQL Analytics Engine
  ├── RAG Retrieval (Qdrant Vector DB for disclosures, policies & notes)
  └── Anti-Hallucination Result Validation Layer
  │
  ▼
LLM Response Generation (Gemini / OpenAI / Deterministic Offline Mode)
  │
  ▼
Final Grounded Response & Validation Metadata
```

---

## 🛠 Features & Deterministic Tools

| Category | Deterministic Tool | Description |
|---|---|---|
| **Totals** | `get_total_credits()` | Total sum of all deposits/credits |
| **Totals** | `get_total_debits()` | Total sum of all withdrawals/expenses |
| **Counts** | `get_transaction_count()` | Total counts of credits, debits, and overall records |
| **Outliers** | `get_highest_credit()` | Largest single deposit transaction |
| **Outliers** | `get_highest_debit()` | Largest single expense transaction |
| **Merchant** | `get_merchant_spending(merchant_name)` | Total spending with a specific merchant (e.g., Amazon, Starbucks) or ranked merchants |
| **Categories** | `get_category_spending(category_name)` | Spending breakdown by category (Groceries, Housing, Dining, Subscriptions, Utilities) |
| **Temporal** | `get_monthly_summary(month, year)` | Monthly income, expenses, and net cash flow trajectory |
| **Temporal** | `get_transactions_by_date_range(start, end)` | Filtered transactions and date-bounded totals |
| **Income** | `get_money_received_sources()` | Identification and ranking of incoming income streams |
| **Expenses** | `get_money_sent_destinations()` | Ranked destinations where money was sent |
| **Recurring** | `get_recurring_transactions()` | Automated detection of subscriptions and periodic bills (Netflix, Spotify, Rent, Utilities) |
| **Balance** | `get_balance_summary()` | Opening balance, closing balance, and net cash flow delta |
| **Top Lists** | `get_top_transactions(n, type)` | Top N transactions sorted deterministically by amount |
| **RAG** | `search_statement_text(query)` | Semantic text search in Qdrant for terms, policies, fees, and footnotes |

---

## 📁 Project Structure

```
bank/
├── app/
│   ├── main.py                  # FastAPI application entrypoint & lifespan
│   ├── api/
│   │   ├── routes.py            # API routes (/upload, /ask, /transactions, /summary, /health)
│   ├── agents/
│   │   ├── state.py             # LangGraph state schema (AgentState)
│   │   └── orchestrator.py      # LangGraph orchestrator state machine & nodes
│   ├── tools/
│   │   ├── analytics_tools.py   # Deterministic financial tools registry (16+ tools)
│   │   └── rag_tools.py         # RAG text retrieval tool
│   ├── models/
│   │   ├── transaction.py       # NormalizedTransaction & FinancialSummary models
│   │   └── schemas.py           # Pydantic API request & response schemas
│   ├── services/
│   │   ├── statement_service.py # Extraction, normalization & storage coordinator
│   │   └── categorizer.py       # Financial rule categorizer & recurring detector
│   ├── extraction/
│   │   ├── base.py              # BaseExtractor interface
│   │   ├── csv_excel_extractor.py # CSV & Excel table extractor
│   │   ├── pdf_extractor.py     # PyMuPDF & pdfplumber PDF extractor
│   │   ├── ocr_extractor.py     # Pytesseract OCR extractor for scans & images
│   │   └── normalizer.py        # Robust bank schema normalizer & header matcher
│   ├── analytics/
│   │   ├── engine.py            # Deterministic Pandas/Python analytics engine
│   │   └── sql_analytics.py     # SQL aggregate queries
│   ├── validation/
│   │   └── validator.py         # Arithmetic consistency & anti-hallucination auditor
│   ├── rag/
│   │   ├── embeddings.py        # Semantic vector embeddings
│   │   └── vector_store.py      # Qdrant vector store integration (:memory: / server)
│   ├── observability/
│   │   └── tracer.py            # Langfuse request & tool tracing
│   ├── database/
│   │   ├── session.py           # SQLAlchemy session & SQLite/PostgreSQL engine
│   │   └── models.py            # Statement and Transaction ORM models
│   └── config/
│       └── settings.py          # Pydantic BaseSettings environment configuration
├── sample_data/                 # Sample CSV, Excel, and PDF bank statements
├── tests/                       # Automated pytest test suites
├── .env.example                 # Environment variables template
├── requirements.txt             # Pinned production dependencies
├── Dockerfile                   # Production Docker container
├── docker-compose.yml           # Multi-container setup (API + PostgreSQL + Qdrant)
└── README.md                    # Documentation
```

---

## 🚀 Quick Start (Local Setup)

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
*Note: If no API keys are configured, the agent automatically runs in high-fidelity deterministic offline mode with 100% functionality!*

### 3. Run Automated Tests
```powershell
python -m pytest tests/ -v
```

### 4. Start the Application
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger UI is available at: **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 🐳 Docker Deployment

To launch the complete production stack (FastAPI + PostgreSQL + Qdrant):
```bash
docker-compose up --build -d
```

---

## 📡 API Usage Examples

### 1. Health Check
```powershell
Invoke-RestMethod -Uri http://localhost:8000/health -Method Get
```

### 2. Upload Bank Statement (`POST /upload`)
Upload a CSV, Excel (.xlsx), or PDF statement:
```powershell
$form = @{
    file = Get-Item -Path "sample_data\chase_statement.csv"
}
$upload = Invoke-RestMethod -Uri http://localhost:8000/upload -Method Post -Form $form
$statementId = $upload.file_id
Write-Host "Uploaded Statement ID: $statementId"
```

### 3. Ask Natural Language Questions (`POST /ask`)
```powershell
# Example 1: Totals
$body = @{
    question = "What is my total credit and debit?"
    session_id = $statementId
} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/ask -Method Post -ContentType "application/json" -Body $body

# Example 2: Merchant spending
$body = @{
    question = "How much did I spend on Amazon?"
    session_id = $statementId
} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/ask -Method Post -ContentType "application/json" -Body $body

# Example 3: Where did money go
$body = @{
    question = "Where did most of my money go?"
    session_id = $statementId
} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/ask -Method Post -ContentType "application/json" -Body $body

# Example 4: Subscriptions
$body = @{
    question = "What are my recurring monthly expenses?"
    session_id = $statementId
} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/ask -Method Post -ContentType "application/json" -Body $body
```

### 4. Query Filtered Transactions (`GET /transactions`)
```powershell
# Retrieve transactions filtered by merchant or category
Invoke-RestMethod -Uri "http://localhost:8000/transactions?merchant=Starbucks&limit=10" -Method Get
```

### 5. High-Level Summary (`GET /summary`)
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/summary?statement_id=$statementId" -Method Get
```

---

## 🛡 Security & Privacy

- **No Hardcoded Secrets**: Sensitive API credentials and database connection strings are managed strictly via environment variables.
- **Data Sanitization**: Bank statements and card numbers (e.g. `*1234`) are sanitized during merchant cleaning.
- **Upload Boundaries**: Strict MIME/extension validation and a 25MB file size limit protect endpoints against malicious or runaway payloads.
- **Anti-Hallucination Auditing**: Every LLM response is checked against actual tool calculation results; discrepancies or invented figures are immediately flagged in the response metadata.

---

## 🔭 Observability with Langfuse

Set `LANGFUSE_ENABLED=true` and provide `LANGFUSE_PUBLIC_KEY` & `LANGFUSE_SECRET_KEY` in `.env`. The agent will automatically trace:
- Full user question journey
- Intent classification and tool routing
- Deterministic calculation duration and payloads
- Token counts, latency, and LLM generations
