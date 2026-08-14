# DataSpeakAI — Conversational Retrieval & Unified AI Assistant Architecture

## 1. Overview
The **Conversational Retrieval & Unified AI Assistant** module transitions DataSpeakAI from isolated, single-turn search dialogs to an enterprise-grade multi-turn conversational intelligence workspace. It bridges unstructured document knowledge bases (RAG via FAISS + BM25) and structured relational databases (NL-to-SQL) into a unified conversational flow with automated intent routing and strict citation grounding.

---

## 2. Architecture & Data Flow Diagram

```
                              ┌────────────────────────┐
                              │  React Frontend UI     │
                              │  (/dashboard/chat)     │
                              └───────────┬────────────┘
                                          │ POST /api/chat
                                          ▼
                              ┌────────────────────────┐
                              │  FastAPI Backend       │
                              │  (routers/chat.py)     │
                              └───────────┬────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     │                                         │
                     ▼                                         ▼
         ┌────────────────────────┐               ┌────────────────────────┐
         │ Conversation & Message │               │ Intelligent Query      │
         │ History Session DB     │               │ Router                 │
         │ (models.Conversation,  │               │ (services/query_router)│
         │  models.Message)       │               └───────────┬────────────┘
         └────────────────────────┘                           │
                                         ┌────────────────────┼────────────────────┐
                                         │                    │                    │
                                         ▼                    ▼                    ▼
                              ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
                              │  RAG Knowledge   │ │  NL-to-SQL       │ │  Hybrid Multi-   │
                              │  Base Retrieval  │ │  Execution       │ │  Source Retrieval│
                              │  (Dense FAISS +  │ │  (Schema context │ │  (Joint RAG +    │
                              │   Sparse BM25 +  │ │   + safe limits  │ │   SQL execution) │
                              │   RRF Fusion)    │ │   + Read-only)   │ │                  │
                              └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
                                       │                    │                    │
                                       └────────────────────┼────────────────────┘
                                                            │
                                                            ▼
                                              ┌───────────────────────────┐
                                              │ Google Gemini 2.5 Flash   │
                                              │ Synthesis Engine          │
                                              │ • Strict inline citations │
                                              │ • Executive data summary  │
                                              │ • Multi-turn memory window│
                                              └─────────────┬─────────────┘
                                                            │
                                                            ▼
                                              ┌───────────────────────────┐
                                              │ Persist Message & Metadata│
                                              │ • Citations & Chunk refs  │
                                              │ • Executed SQL & Tables   │
                                              │ • QueryLog recording      │
                                              └─────────────┬─────────────┘
                                                            │
                                                            ▼
                                              ┌───────────────────────────┐
                                              │ Structured ChatResponse   │
                                              └───────────────────────────┘
```

---

## 3. Core Capabilities & Components

### 3.1 Data Layer (`backend/models.py`, `backend/schemas.py`)
* **`Conversation`**: Tracks tenant session threads, auto-generated title (from first user prompt), platform (`web`, `widget`, `api`), creation and updated timestamps.
* **`Message`**: Stores individual conversation turns (`user`, `assistant`, `system`), query type classification (`rag`, `sql`, `hybrid`), and `metadata_json` containing chunk citations, SQL queries, row previews, and execution metrics.
* **`QueryLog`**: Automatically logs SQL queries and execution times for auditability and analytics.

### 3.2 Intelligent Query Routing (`backend/services/query_router.py`)
* **Manual Override**: Supports explicit user preference override (`auto`, `documents`, `database`).
* **Tenant Asset Introspection**: Automatically verifies whether tenant has uploaded documents and/or connected databases.
* **Keyword & Schema Heuristics**: Analyzes numerical, aggregation, or document keywords, as well as introspected table names from connected databases.
* **LLM Intent Classifier (Gemini 2.5 Flash)**: Light-weight classifier fallback resolving ambiguous questions into `RAG`, `SQL`, or `HYBRID`.
* **Automated Database Selection (Option C)**: Automatically introspects schema metadata across all tenant databases to target the most relevant database connection.

### 3.3 Multi-Modal Grounded RAG Retrieval (`backend/routers/chat.py`)
* **Hybrid Dense-Sparse Search**:
  * Dense semantic search via `FAISS` with `SentenceTransformer` (`all-MiniLM-L6-v2`, 384 dimensions).
  * Sparse keyword search via `BM25Okapi` (`BM25IndexManager`).
  * Rank combination using **Reciprocal Rank Fusion (RRF)**: $\text{RRF}(d) = \sum \frac{1}{60 + \text{rank}(d)}$.
  * Cross-encoder re-ranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
* **Strict Citations**: Extracts source document names, page numbers (`p. X`), and extracted snippet references (`[Source: filename, p. X]`).

### 3.4 Structured SQL Database Execution
* Schema introspection formatted dynamically into prompt context.
* SQL guardrails enforcing read-only queries and automatic `LIMIT` capping.
* Conversational tabular summaries synthesizing natural language insights from returned rows.

### 3.5 React Conversational UI (`src/app/pages/dashboard/ChatPage.tsx`)
* **Responsive 3-Panel Workspace**:
  * Left sidebar with session search, new chat creation, rename, delete, and timestamped history.
  * Main conversation stream with user/assistant bubbles, source engine badges, interactive SQL tables, and collapsible citation cards.
  * Modal drawer for inspecting full grounded chunk snippets.
  * Top engine switcher toggle: `Auto`, `Knowledge Base (RAG)`, `Database (SQL)`.
