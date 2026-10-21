# 5.4 Unit Testing: RAG Knowledge Base & Document Ingestion Engine

### Testing Objective
To thoroughly evaluate and verify the functional correctness, multi-tenant security isolation, indexing precision, and retrieval performance of the **DataSpeakAI RAG Knowledge Base & Document Ingestion Engine**.

Testing validates the entire **End-to-End RAG Intelligence Pipeline**:
1. **Document Validation & Security Controls** — Magic file header signature verification (rejecting binary spoofing) and enforced 25 MB payload size ceiling.
2. **Text Extraction & Multi-Strategy Chunking** — LangChain recursive text partitioning with configurable chunk sizes (e.g. 512 tokens) and overlap windows (50 tokens).
3. **Dense Vector Embeddings & FAISS Storage** — Local vector index creation using HuggingFace `SentenceTransformer` (`all-MiniLM-L6-v2`) with tenant isolation.
4. **Sparse BM25 Keyword Search & Hybrid Fusion** — Term frequency scoring fused with dense vector retrieval via Reciprocal Rank Fusion (RRF).
5. **Real-time Pipeline Heartbeat & Tombstoning** — Ingestion progress tracking (`queued` $\rightarrow$ `completed`), durable content-addressed storage, and immediate vector deletion on tombstoning.

---

### Table 5.4: RAG Knowledge Base & Document Ingestion Unit Test Cases

| No. | Test case / Test script | Attribute and value | Expected result | Actual Result |
| :---: | :--- | :--- | :--- | :---: |
| **1** | Check document catalog listing and tenant scoping | `endpoint: 'GET /api/documents'`<br>`tenant_id: 1` | Returns HTTP 200 with list of tenant documents, statuses, file types, and embedding counts. | **Pass** |
| **2** | Check semantic document chunk extraction and retrieval | `endpoint: 'GET /api/documents/{id}/chunks'`<br>`document_id: 1` (`AI Engineering.pdf`) | Returns HTTP 200 with segmented text chunks, chunk indices, and word count metadata. | **Pass** |
| **3** | Check real-time document ingestion lifecycle status | `endpoint: 'GET /api/documents/{id}/status'`<br>`document_id: 1` | Returns HTTP 200 with pipeline stage (`Completed`), progress float (`1.0`), and heartbeat. | **Pass** |
| **4** | Check cross-tenant document isolation & access denial | `document_id: 999999`<br>`tenant_id: 1` (unowned ID) | Blocks cross-tenant enumeration and returns HTTP 404 Not Found without leaking metadata. | **Pass** |
| **5** | Check hybrid RAG search with Reciprocal Rank Fusion (RRF) | `query: 'What are the core engineering concepts?'`<br>`mode: 'hybrid'`, `synthesize: True` | Returns HTTP 200 with ranked document chunks and synthesized AI response with inline citations. | **Pass** |
| **6** | Check semantic dense vector search via FAISS cosine index | `query: 'Foundation models'`, `mode: 'semantic'`<br>`top_k: 2`, `synthesize: False` | Returns top-k dense vector matches with valid similarity scores and verified metadata. | **Pass** |
| **7** | Check search metadata filtering (`document_ids` & `content_types`) | `document_ids: [1]`, `content_types: ['text']`<br>`mode: 'hybrid'` | Restricts search chunks strictly to specified document ID and text modality without false matches. | **Pass** |
| **8** | Check file magic header signature validation & spoofing defense | `file: 'malicious.pdf'` with `MZ` executable header<br>`file: 'report.pdf'` with `%PDF-1.4` header | Rejects executable spoofing attempt with HTTP 400 and validates genuine `%PDF-` magic bytes. | **Pass** |
| **9** | Check file upload size ceiling (25MB HTTP 413 guard) | `MAX_FILE_SIZE = 25 * 1024 * 1024` bytes<br>`oversized: 26 MB` | Enforces strict 25MB boundary limit preventing memory exhaustion DOS attacks. | **Pass** |
| **10** | Check recursive character chunking with configured overlap | `chunk_size: 200`, `chunk_overlap: 30`<br>`text_splitter: RecursiveCharacterTextSplitter` | Partitions text cleanly without semantic truncation and maintains consistent overlap window. | **Pass** |
| **11** | Check sparse BM25 inverted index tokenization and ranking | `engine: BM25IndexManager(tenant_id=1)`<br>`method: bm25_manager.search` | Initializes tokenized inverted index for exact term matching and frequency scoring. | **Pass** |
| **12** | Check document audit persistence & active status flags | `document_id: 1`<br>`models.Document.is_deleted == False` | Confirms document integrity, storage key persistence, and uncorrupted state in SQLite. | **Pass** |

---

### Test Execution Summary
* **Total Unit Tests Executed:** 12
* **Passed:** 12 (100%)
* **Failed:** 0 (0%)
* **Average Execution Latency:** 862 ms
* **Test Runner Environment:** Python 3.10+ / FastAPI / FAISS (`faiss-cpu`) / HuggingFace `all-MiniLM-L6-v2` / LangChain / SQLite / Pydantic v2
* **Target Knowledge Base Documents:** `AI Engineering.pdf` (2,665 chunks, 5.7 MB) & `Student Card.pdf` (3 chunks, 867 KB)

---

### Visual Proof & Automated Execution Screenshots

#### Figure 5.4.1: Knowledge Base Document Catalog & Management Interface
Verified rendering of the live tenant Knowledge Base table showing uploaded PDFs (`AI Engineering.pdf` and `Student Card.pdf`), file size, upload dates, `Completed` processing status badges, embedding counts (2,665 chunks), and action menus.

![Knowledge Base Document Catalog](assets/knowledge_base/knowledge_base_overview.png)

---

#### Figure 5.4.2: Interactive Test AI Knowledge Base Search Dialog
Verified interactive Test AI Knowledge Base modal featuring multi-modal search filters: Search Mode (`Hybrid (BM25 + FAISS)`), Document filter picker, Content Types (`Text`, `Table`, `Image`), Page Range bounds, query input, and real-time execution.

![Interactive Test AI Query Modal with Filters](assets/knowledge_base/knowledge_base_test_query.png)

---

#### Figure 5.4.3: Document Embeddings & Semantic Chunk Text Viewer
Verified Document Embeddings modal displaying segmented text chunks extracted from `AI Engineering.pdf`, showing Chunk indices (`Chunk 1`, `Chunk 2`), character contents, and semantic token preservation.

![Document Embeddings and Chunks Inspector](assets/knowledge_base/knowledge_base_chunks_modal.png)

---

#### Figure 5.4.4: Document Upload & Chunking Strategy Configuration Interface
Verified Document Upload page (`/dashboard/upload-documents`) featuring the drag-and-drop file upload zone, Chunk Size slider (default 512 tokens), Chunk Overlap slider (50 tokens), and Chunking Strategy selector (`paragraph`, `fixed`, `sentence`).

![Document Upload and Chunking Strategy Configuration](assets/knowledge_base/knowledge_base_upload_page.png)
