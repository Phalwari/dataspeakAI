# DataSpeakAI — Complete RAG & Conversational Retrieval Architecture

## 1. System Overview & Platform Vision

**DataSpeakAI** is an enterprise-grade Conversational AI & Business Intelligence SaaS platform designed to bridge the gap between unstructured business documents (PDFs, DOCX, Spreadsheets, Presentations, Web pages), structured relational databases (PostgreSQL, MySQL, SQLite), and end-user decision making.

The system features a **Multi-Modal Hybrid RAG (Retrieval-Augmented Generation)** architecture integrated with dense vector search (FAISS), sparse keyword indexing (BM25), Reciprocal Rank Fusion (RRF), cross-encoder re-ranking, and Google Gemini 2.5 Flash.

---

## 2. End-to-End System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                   DOCUMENT INGESTION STAGE                               │
│                                                                                          │
│   Uploaded Document (PDF, DOCX, XLSX, PPTX, CSV, HTML, MD, TXT)                          │
│                                  │                                                       │
│                                  ▼                                                       │
│             ┌──────────────────────────────────────────┐                                 │
│             │ Structure-Aware Pre-Flight Evaluator     │                                 │
│             │ • Text length check (> 100 chars/page)   │                                 │
│             │ • Visual image / scanned page detection  │                                 │
│             └────────────────────┬─────────────────────┘                                 │
│                                  │                                                       │
│                   ┌──────────────┴──────────────┐                                        │
│                   ▼                             ▼                                        │
│         ┌──────────────────┐          ┌──────────────────┐                               │
│         │ Fast CPU Parser  │          │ Gemini 2.5 Flash │                               │
│         │ (PyMuPDF /       │          │ VLM OCR & Chart  │                               │
│         │  pdfplumber)     │          │ Comprehension    │                               │
│         └────────┬─────────┘          └────────┬─────────┘                               │
│                  │                             │                                         │
│                  └──────────────┬──────────────┘                                         │
│                                 │                                                        │
│                                 ▼                                                        │
│             ┌──────────────────────────────────────────┐                                 │
│             │ Table Matrix & Visual Extraction         │                                 │
│             │ • Detected grids -> Clean HTML/Markdown  │                                 │
│             │ • Anchored with [[TABLE_REF_001]]        │                                 │
│             └───────────────────┬──────────────────────┘                                 │
│                                 │                                                        │
│                                 ▼                                                        │
│             ┌──────────────────────────────────────────┐                                 │
│             │ Chunking Engine (Recursive Splitter)     │                                 │
│             │ • Narrative text (512 tokens / 50 ovlp)  │                                 │
│             │ • Tables & Visuals preserved intact      │                                 │
│             └───────────────────┬──────────────────────┘                                 │
│                                 │                                                        │
│                   ┌─────────────┴─────────────┐                                          │
│                   ▼                           ▼                                          │
│         ┌──────────────────┐        ┌──────────────────┐                                 │
│         │ Dense Embeddings │        │ Sparse BM25      │                                 │
│         │ all-MiniLM-L6-v2 │        │ Inverted Index   │                                 │
│         │ ➔ FAISS Index    │        │ ➔ bm25.pkl       │                                 │
│         └──────────────────┘        └──────────────────┘                                 │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                   RETRIEVAL & QUERY STAGE                                │
│                                                                                          │
│         User Query: "What are the compliance rules and Q3 revenue numbers?"              │
│                                  │                                                       │
│                                  ▼                                                       │
│             ┌──────────────────────────────────────────┐                                 │
│             │ Intelligent Query Router                 │                                 │
│             │ (RAG vs NL-to-SQL vs Hybrid Classifier)  │                                 │
│             └────────────────────┬─────────────────────┘                                 │
│                                  │                                                       │
│                   ┌──────────────┴──────────────┐                                        │
│                   ▼                             ▼                                        │
│         ┌──────────────────┐          ┌──────────────────┐                               │
│         │ Dense Search     │          │ Sparse Search    │                               │
│         │ (FAISS k=40)     │          │ (BM25 top 40)    │                               │
│         └────────┬─────────┘          └────────┬─────────┘                               │
│                  │                             │                                         │
│                  └──────────────┬──────────────┘                                         │
│                                 │                                                        │
│                                 ▼                                                        │
│             ┌──────────────────────────────────────────┐                                 │
│             │ Metadata Pre / Post Filtering            │                                 │
│             │ (Document IDs, Content Types, Pages)     │                                 │
│             └───────────────────┬──────────────────────┘                                 │
│                                 │                                                        │
│                                 ▼                                                        │
│             ┌──────────────────────────────────────────┐                                 │
│             │ Reciprocal Rank Fusion (RRF)             │                                 │
│             │ Merges & normalizes dense + sparse lists │                                 │
│             └───────────────────┬──────────────────────┘                                 │
│                                 │                                                        │
│                                 ▼                                                        │
│             ┌──────────────────────────────────────────┐                                 │
│             │ Cross-Encoder Re-Ranking (MS-MARCO)      │                                 │
│             │ Deep query-passage cross-attention score │                                 │
│             └───────────────────┬──────────────────────┘                                 │
│                                 │                                                        │
│                                 ▼                                                        │
│             ┌──────────────────────────────────────────┐                                 │
│             │ Google Gemini 2.5 Flash Synthesis Engine │ ◄── Multi-turn History (8 turns)│
│             │ • Strict inline citations [Source: p. X] │                                 │
│             │ • SQL tabular summary & data integration │                                 │
│             └───────────────────┬──────────────────────┘                                 │
│                                 │                                                        │
│                                 ▼                                                        │
│         Interactive Chat Bubble + Citation Cards + SQL Grid Table                        │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Multi-Format Ingestion Engine: How Different Files Are Handled

Different enterprise document types carry different data topologies (tabular numbers, narrative text, visual graphs, slides, or scanned pages). DataSpeakAI implements **specialized, format-aware extraction routing** (`backend/ingestion/extractors.py`):

```
                                  Uploaded Document File
                                            │
         ┌───────────────┬──────────────────┼──────────────────┬────────────────┐
         ▼               ▼                  ▼                  ▼                ▼
    PDF (.pdf)      DOCX (.docx)    Excel / CSV (.xlsx, .csv) PPTX (.pptx) HTML / MD / TXT
         │               │                  │                  │                │
 ┌───────┴───────┐   Heading Hierarchy   Pandas Sheet Parse    Slide-by-Slide   DOM / Text Clean
 │ Pre-Flight:   │   + Table Matrix      + Clean Nulls         Text Frame +     (BeautifulSoup)
 │ Text vs Image │   Extraction          + HTML/MD Tables      Speaker Notes
 └───────┬───────┘
         │
   ┌─────┴─────┐
   ▼           ▼
Digital     Scanned / Visual
Text &      (Gemini 2.5 Flash
Tables      200 DPI VLM OCR)
```

---

### 3.1 PDF Documents (`.pdf`)

PDF processing uses a **Dual-Path Structure Router** (`extract_pdf_split_router`):

#### A. Standard Digital / Text-Heavy PDFs (Fast CPU Route)
* **Pre-Flight Assessment**: `PyMuPDF` (`fitz`) evaluates text density page-by-page. If clean text length $> 100$ characters and no embedded diagrams exist, the page enters the Fast CPU path.
* **Text Parsing**: Digital text streams are parsed preserving whitespace, paragraph boundaries, and page numbers.
* **Table Extraction**: `pdfplumber` analyzes explicit grid lines and whitespace bounding boxes to isolate tables into structured matrix formats without slicing columns.
* **Performance**: Sub-second extraction per page running entirely on CPU.

#### B. Scanned / Non-Searchable PDFs (Visual OCR Route)
* **Trigger Condition**: Scanned invoices, signed agreements, or physical document scans where text character count $\le 100$ characters.
* **In-Memory Pixmap Generation**: `fitz.Page.get_pixmap(dpi=200)` renders the scanned page directly into an in-memory PNG byte buffer (no disk I/O).
* **Gemini 2.5 Flash VLM OCR**: The image is base64-encoded and sent to Google Gemini 2.5 Flash via REST API with instructions to reconstruct text, headings, and structure in Markdown format.

#### C. Complex PDF Reports with Graphs, Charts & Visual Figures
* **The Problem**: Standard text extractors discard or corrupt visual information (bar charts, pie charts, system architecture diagrams, visual KPI cards).
* **The Solution**:
  1. `fitz` inspects the page for embedded images and drawings (`page.get_images()`).
  2. If visual charts are detected, the visual page is rendered at 200 DPI and dispatched to Google Gemini 2.5 Flash.
  3. The prompt explicitly instructs Gemini:
     > *"Perform high-precision OCR on this document page. Reconstruct narrative text and tabular data into clean Markdown. Describe any key visual figures, trends, or charts present."*
  4. The visual explanation and numerical trends from the chart (e.g. *"Figure 3 shows quarterly active users growing from 10k in Q1 to 45k in Q4"*) are stored as a dedicated **Visual Chunk** with `content_type="image"`.
  5. This allows users to query questions like *"What trend does the revenue chart show?"* and receive grounded, accurate answers.

---

### 3.2 Tables Inside Documents & PDFs

Tables represent structured numerical or tabular data embedded in unstructured documents. If standard character-count chunking is used, rows and headers get cut in half across chunk boundaries.

DataSpeakAI handles tables via **Table Matrix Preservation & Placeholder Anchoring**:

1. **Dual Matrix Serialization**:
   Tables are extracted as both Markdown matrices and standalone HTML tables:
   ```markdown
   | Quarter | Revenue (M$) | YoY Growth | Operating Margin |
   | --- | --- | --- | --- |
   | Q1 2025 | $12.4M | +14% | 22.1% |
   | Q2 2025 | $14.8M | +18% | 24.5% |
   | Q3 2025 | $16.2M | +15% | 23.8% |
   ```
2. **Anchor Tags in Narrative Text**:
   The table is replaced in the main text stream with a unique reference tag: `[[TABLE_REF_001]]`. This keeps the surrounding narrative flow clean while preserving exact table context.
3. **Chunk Splitting Bypass (Critical Guardrail)**:
   Table blocks **bypass character splitting completely**. They are saved intact as whole chunks with `content_type="table"` and `reference_id="TABLE_REF_001"`.
4. **Result**: Schema definitions, header alignments, and row-column relationships are 100% preserved during vector and keyword search.

---

### 3.3 Spreadsheets & Delimited Files: Excel (`.xlsx`, `.xls`) & CSV (`.csv`)

Spreadsheet files (`extract_excel_csv`) contain dense tabular datasets:

* **Engine**: Powered by Python `pandas` and `openpyxl`.
* **Multi-Sheet Traversal**: Traverses all sheets in an Excel workbook (e.g. `Sheet1`, `Q3_Forecast`, `Employees`).
* **Data Sanitization**: Automatically fills null values (`NaN` $\to$ `""`), formats numerical timestamps, and standardizes column headers.
* **Sheet-to-Table Conversion**: Each sheet is converted into a standalone Markdown/HTML table block and anchored with a sheet header:
  ```markdown
  ## Sheet: Q3_Forecast
  [[TABLE_REF_002]]
  ```
* **Search Optimization**: Both column headers and individual row values are indexed into BM25 and FAISS, allowing queries like *"What was the forecast for APAC in Q3?"* to retrieve the exact table slice.

---

### 3.4 Microsoft Word Documents (`.docx`)

Word documents (`extract_docx`) contain rich hierarchical formatting:

* **Engine**: Built with `python-docx`.
* **Heading Hierarchy Preservation**: Inspects paragraph styles (`Heading 1`, `Heading 2`, `Heading 3`) and translates them into Markdown headings (`# Title`, `## Section`).
* **Table Isolation**: Extracts embedded Word tables row-by-row into HTML/Markdown blocks, assigning sequential `TABLE_REF_XXX` identifiers.
* **Section Heading Attribution**: Each chunk is tagged with its parent `section_heading` in `models.DocumentChunk`, helping the retrieval engine understand document hierarchy.

---

### 3.5 Microsoft PowerPoint Presentations (`.pptx`)

Presentations (`extract_pptx`) contain fragmented, slide-oriented information:

* **Engine**: Built with `python-pptx`.
* **Slide-by-Slide Segmentation**: Traverses presentation slides sequentially.
* **Text Frame Extraction**: Aggregates titles, subtitle text, text boxes, and bullet lists per slide.
* **Slide Demarcation**: Formats chunks with explicit slide numbers:
  ```
  --- Slide 4: Strategic Priorities for 2026 ---
  • Expand enterprise RAG capabilities
  • Accelerate NL-to-SQL query accuracy
  ```
* **Page Mapping**: `page_number` in `DocumentChunk` directly maps to the presentation slide number.

---

### 3.6 Web Pages, Markdown & Plain Text (`.html`, `.htm`, `.md`, `.txt`)

* **HTML Parsing**: `extract_html_md` uses `BeautifulSoup` (`bs4`) to strip extraneous scripts, styles, and boilerplate navigation headers, retaining clean structural body text.
* **Markdown & Plain Text**: Streamed directly with UTF-8 encoding normalization and clean newline handling.

---

## 4. Summary Matrix of Supported Document Formats

| Format | Extensions | Primary Libraries | Extraction Route | Table Handling | Visual Handling |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PDF (Digital)** | `.pdf` | `fitz` (PyMuPDF), `pdfplumber` | Fast CPU text extraction | Grid cell boundary detection $\to$ Markdown/HTML matrix | Image count tracking |
| **PDF (Scanned)** | `.pdf` | `fitz`, Google Gemini 2.5 Flash | Visual Escalation (200 DPI in-memory PNG) | Gemini OCR Markdown table reconstruction | Full-page visual OCR |
| **PDF (Charts/Visuals)** | `.pdf` | `fitz`, Google Gemini 2.5 Flash | Visual VLM Prompting | Extracted via `pdfplumber` or Gemini | Dedicated `image` chunk with visual trend description |
| **Word** | `.docx` | `python-docx` | Heading hierarchy parsing | Word tables $\to$ Standalone HTML/Markdown chunks | Paragraph hierarchy preservation |
| **Spreadsheets** | `.xlsx`, `.xls` | `pandas`, `openpyxl` | Multi-sheet DataFrame traversal | Cleaned tabular matrices with header preservation | Sheet-by-sheet isolation |
| **CSV** | `.csv` | `pandas` | Clean NaN tabular reader | CSV rows $\to$ Structured Markdown table | Fast tabular indexing |
| **Presentations** | `.pptx` | `python-pptx` | Slide shape & text frame extraction | Slide tables converted to Markdown | Slide number mapping |
| **Web & Plaintext** | `.html`, `.md`, `.txt` | `BeautifulSoup`, UTF-8 streamer | DOM text stripping & clean streaming | Preserved HTML/MD table blocks | Pure text formatting |

---

## 5. Chunking Logic & Database Storage Model

```
Narrative Text Stream
       │
       ▼
┌──────────────────────────────────────────────┐
│ LangChain RecursiveCharacterTextSplitter    │
│ • chunk_size = 512 tokens                    │
│ • chunk_overlap = 50 tokens                  │
│ • Separators: \n\n -> \n -> [. ! ?]          │
└──────────────────────┬───────────────────────┘
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
Standard Text Chunks            Standalone Table Chunks
(content_type="text")           (content_type="table", bypass split)
       │                               │
       └───────────────┬───────────────┘
                       ▼
         SQLite document_chunks Table
         • document_id
         • page_number
         • chunk_index
         • content_type ("text" | "table" | "image")
         • section_heading
         • reference_id ("TABLE_REF_001")
```

### Key Chunking Principles:
1. **Context Overlap (50 tokens)**: Prevents sentences and factual statements from being split arbitrarily across boundaries.
2. **Table & Image Chunk Isolation**: Tables and visual explanations never undergo character splitting, preventing mangled markdown or severed numbers.
3. **Metadata Enrichment**: Every chunk in `document_chunks` records its source document, page number, section heading, content type, and anchor reference.

---

## 6. Retrieval & Multi-Turn Synthesis Engine

### 6.1 Intelligent Query Routing (`backend/services/query_router.py`)
User queries are automatically classified before search:
* **`RAG`**: Questions about documents, policies, contracts, handbook clauses, and textual reports.
* **`SQL`**: Questions with aggregations (`SUM`, `COUNT`, `AVG`), table names, or structured database filters.
* **`HYBRID`**: Questions combining structured numerical statistics and qualitative document explanations.
* **Option C Auto-DB Selection**: Automatically matches query keywords against introspected table names to pick the best database connection.

### 6.2 5-Stage Hybrid Search Pipeline
1. **Dense Semantic Search (FAISS)**: Top 40 nearest neighbors encoded via `SentenceTransformer` (`all-MiniLM-L6-v2`, 384 dims).
2. **Sparse Keyword Search (BM25)**: Top 40 hits scored via `BM25Okapi` inverted index for exact product codes, acronyms, and names.
3. **Metadata Filtering**: Filter candidates by `document_ids`, `content_types` (`text`, `table`, `image`), and `page_range`.
4. **Reciprocal Rank Fusion (RRF)**:
   $$\text{RRF}(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{60 + \text{rank}_m(d)}$$
5. **Cross-Encoder Re-Ranking**: Candidate pairs scored with `cross-encoder/ms-marco-MiniLM-L-6-v2` for maximum precision.

### 6.3 LLM Answer Synthesis & Citation Grounding (`backend/routers/chat.py`)
* Prepends the last 8 messages of conversation history for multi-turn continuity.
* Dispatches formatted context chunks with source tags (`[Document Chunk #1 - Source: Annual_Report.pdf, Page 12]`) to **Google Gemini 2.5 Flash**.
* Enforces strict inline citation tags: `[Source: filename, p. X]`.
* Formats response into interactive **Source Citation Cards** and **SQL Data Grids** on the React UI ([`ChatPage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/ChatPage.tsx)).
