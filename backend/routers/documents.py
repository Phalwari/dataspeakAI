from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
import models, schemas
from database import get_db
from dependencies import get_current_user
import os
import io

# Move heavy imports inside functions to prevent OOM on startup
has_ai_libs = True 

router = APIRouter(prefix="/api/documents", tags=["documents"])

os.makedirs("uploads", exist_ok=True)
os.makedirs("vector_store", exist_ok=True)

# We use a global variable to load embeddings once
embeddings_model = None

def table_to_markdown(table):
    if not table or not table[0]:
        return ""
    # Convert cell values to clean strings and remove nested newlines to avoid breaking markdown formatting
    clean_table = []
    for row in table:
        clean_table.append([str(cell or "").strip().replace("\n", " ") for cell in row])
        
    headers = clean_table[0]
    if not any(headers):
        headers = [f"Column {i+1}" for i in range(len(headers))]
        
    markdown = f"| {' | '.join(headers)} |\n"
    markdown += f"| {' | '.join(['---'] * len(headers))} |\n"
    
    for row in clean_table[1:]:
        markdown += f"| {' | '.join(row)} |\n"
    return markdown

import uuid
from ingestion.extractors import (
    extract_pdf_split_router, extract_docx, extract_excel_csv, 
    extract_pptx, extract_html_md
)
from search.bm25_index import BM25IndexManager
from search.hybrid import reciprocal_rank_fusion, cross_encoder_rerank

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB Limit

def process_document(document_id: int, file_path: str, tenant_id: int, chunk_size: int, chunk_overlap: int, strategy: str, db: Session):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc: return

    try:
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        ext = os.path.splitext(file_path)[1].lower()
        
        # 1. Extract content based on file extension
        if ext == '.pdf':
            extracted = extract_pdf_split_router(file_path, gemini_api_key)
        elif ext == '.docx':
            extracted = extract_docx(file_path)
        elif ext in ['.xlsx', '.xls', '.csv']:
            extracted = extract_excel_csv(file_path)
        elif ext in ['.pptx', '.ppt']:
            extracted = extract_pptx(file_path)
        elif ext in ['.html', '.htm', '.md']:
            extracted = extract_html_md(file_path)
        else:
            # Fallback text extractor
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            from ingestion import ExtractedContent, NarrativeBlock
            extracted = ExtractedContent()
            extracted.narrative_chunks.append(NarrativeBlock(text=text, page_number=1))
            extracted.stats.total_pages = 1
            extracted.stats.pages_processed = 1

        # Update stats on document
        doc.total_pages = extracted.stats.total_pages
        doc.visual_pages = extracted.stats.visual_pages
        doc.table_count = extracted.stats.table_count
        doc.image_count = extracted.stats.image_count
        doc.progress = 0.3
        db.commit()

        # 2. Chunk Narrative Blocks
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        all_chunks = []
        all_metadatas = []

        for block in extracted.narrative_chunks:
            sub_chunks = text_splitter.split_text(block.text)
            for sub_text in sub_chunks:
                all_chunks.append(sub_text)
                all_metadatas.append({
                    "document_id": document_id,
                    "source": doc.name,
                    "page_number": block.page_number,
                    "content_type": "text",
                    "section_heading": block.section_heading
                })

        for tbl in extracted.table_chunks:
            all_chunks.append(tbl.html_content)
            all_metadatas.append({
                "document_id": document_id,
                "source": doc.name,
                "page_number": tbl.page_number,
                "content_type": "table",
                "reference_id": tbl.reference_id
            })

        for vis in extracted.visual_chunks:
            all_chunks.append(vis.description)
            all_metadatas.append({
                "document_id": document_id,
                "source": doc.name,
                "page_number": vis.page_number,
                "content_type": "image",
                "reference_id": vis.reference_id
            })

        doc.progress = 0.6
        db.commit()

        # 3. Create/Load FAISS
        global embeddings_model
        if embeddings_model is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        index_path = f"vector_store/tenant_{tenant_id}"
        from langchain_community.vectorstores import FAISS
        if os.path.exists(index_path):
            vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
            vectorstore.add_texts(texts=all_chunks, metadatas=all_metadatas)
        else:
            vectorstore = FAISS.from_texts(texts=all_chunks, embedding=embeddings_model, metadatas=all_metadatas)

        vectorstore.save_local(index_path)

        # 4. Save to DocumentChunk SQL table & update BM25
        db_chunk_objects = []
        for i, (chunk_text, meta) in enumerate(zip(all_chunks, all_metadatas)):
            db_chunk = models.DocumentChunk(
                document_id=document_id,
                content=chunk_text,
                overlap_chars=chunk_overlap,
                chunk_index=i,
                page_number=meta.get("page_number"),
                content_type=meta.get("content_type", "text"),
                section_heading=meta.get("section_heading"),
                reference_id=meta.get("reference_id")
            )
            db.add(db_chunk)
            db_chunk_objects.append(db_chunk)

        doc.status = "Completed"
        doc.embeddings_count = len(all_chunks)
        doc.pages_processed = doc.total_pages
        doc.progress = 1.0
        db.commit()

        # Build BM25 index for tenant
        all_tenant_chunks = db.query(models.DocumentChunk).join(models.Document).filter(
            models.Document.tenant_id == tenant_id
        ).all()
        
        bm25_input = [
            {
                "id": c.id,
                "content": c.content,
                "metadata": {
                    "document_id": c.document_id,
                    "chunk_index": c.chunk_index,
                    "page_number": c.page_number,
                    "content_type": c.content_type,
                    "reference_id": c.reference_id,
                    "source": doc.name
                }
            } for c in all_tenant_chunks
        ]
        bm25_manager = BM25IndexManager(tenant_id=tenant_id)
        bm25_manager.build_index(bm25_input)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error processing document: {e}")
        doc.status = "Failed"
        doc.error_message = str(e)
        doc.progress = 0.0
        db.commit()

    finally:
        # File Cleanup after processing
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as clean_err:
                print(f"Failed to cleanup temp file {file_path}: {clean_err}")

def reembed_stored_chunks(document_id: int, tenant_id: int, db: Session = None):
    close_db = False
    if db is None:
        from database import SessionLocal
        db = SessionLocal()
        close_db = True

    try:
        doc = db.query(models.Document).filter(models.Document.id == document_id).first()
        if not doc:
            return

        doc.status = "Processing"
        doc.progress = 0.1
        db.commit()

        global embeddings_model
        model_name = doc.embedding_model or "all-MiniLM-L6-v2"
        if embeddings_model is None or getattr(embeddings_model, "model_name", None) != model_name:
            from langchain_huggingface import HuggingFaceEmbeddings
            embeddings_model = HuggingFaceEmbeddings(model_name=model_name)

        index_path = f"vector_store/tenant_{tenant_id}"
        if os.path.exists(index_path):
            from langchain_community.vectorstores import FAISS
            vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
            docstore_dict = vectorstore.docstore._dict
            ids_to_delete = [uid for uid, doc_data in docstore_dict.items() if doc_data.metadata.get("document_id") == document_id]
            if ids_to_delete:
                vectorstore.delete(ids_to_delete)
                vectorstore.save_local(index_path)

        doc.progress = 0.3
        db.commit()

        db_chunks = db.query(models.DocumentChunk).filter(
            models.DocumentChunk.document_id == document_id
        ).order_by(models.DocumentChunk.chunk_index).all()

        if db_chunks:
            all_chunks = [c.content for c in db_chunks]
            all_metadatas = [{
                "document_id": document_id,
                "source": doc.name,
                "page_number": c.page_number,
                "content_type": c.content_type,
                "section_heading": c.section_heading,
                "reference_id": c.reference_id
            } for c in db_chunks]

            doc.progress = 0.6
            db.commit()

            from langchain_community.vectorstores import FAISS
            if os.path.exists(index_path):
                vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
                vectorstore.add_texts(texts=all_chunks, metadatas=all_metadatas)
            else:
                vectorstore = FAISS.from_texts(texts=all_chunks, embedding=embeddings_model, metadatas=all_metadatas)

            vectorstore.save_local(index_path)

        all_tenant_chunks = db.query(models.DocumentChunk).join(models.Document).filter(
            models.Document.tenant_id == tenant_id
        ).all()

        bm25_input = [
            {
                "id": c.id,
                "content": c.content,
                "metadata": {
                    "document_id": c.document_id,
                    "chunk_index": c.chunk_index,
                    "page_number": c.page_number,
                    "content_type": c.content_type,
                    "reference_id": c.reference_id,
                    "source": doc.name
                }
            } for c in all_tenant_chunks
        ]
        bm25_manager = BM25IndexManager(tenant_id=tenant_id)
        bm25_manager.build_index(bm25_input)

        doc.status = "Completed"
        doc.embeddings_count = len(db_chunks)
        doc.progress = 1.0
        doc.error_message = None
        db.commit()

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error reindexing document {document_id}: {e}")
        doc.status = "Failed"
        doc.error_message = str(e)
        doc.progress = 0.0
        db.commit()
    finally:
        if close_db:
            db.close()

@router.get("", response_model=list[schemas.DocumentResponse])
def get_documents(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    return db.query(models.Document).filter(models.Document.tenant_id == current_user.tenant_id).all()

@router.post("/upload", response_model=schemas.DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    chunk_size: int = Form(512),
    chunk_overlap: int = Form(50),
    chunking_strategy: str = Form("fixed"),
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    # Streaming file read with 100MB size limit check
    file_size = 0
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = f"uploads/{unique_filename}"

    with open(file_path, "wb") as f:
        while chunk := await file.read(8192):
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE:
                f.close()
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(status_code=400, detail=f"File exceeds maximum allowed size of 100MB")
            f.write(chunk)
        
    ext = os.path.splitext(file.filename)[1].upper().replace('.', '') or "TXT"
    doc = models.Document(
        tenant_id=current_user.tenant_id,
        name=file.filename,
        file_type=ext,
        size=file_size,
        status="Processing",
        embeddings_count=0,
        progress=0.05
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    if os.getenv("CELERY_BROKER_URL"):
        from ingestion.task_queue import process_document_task
        task = process_document_task.delay(doc.id, file_path, current_user.tenant_id, chunk_size, chunk_overlap, chunking_strategy)
        doc.celery_task_id = task.id
        db.commit()
    else:
        background_tasks.add_task(process_document, doc.id, file_path, current_user.tenant_id, chunk_size, chunk_overlap, chunking_strategy, db)
    
    return doc

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    doc = db.query(models.Document).filter(
        models.Document.id == document_id, 
        models.Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    try:
        global embeddings_model
        if embeddings_model is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        index_path = f"vector_store/tenant_{current_user.tenant_id}"
        if os.path.exists(index_path):
            from langchain_community.vectorstores import FAISS
            vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
            docstore_dict = vectorstore.docstore._dict
            ids_to_delete = [uid for uid, doc_data in docstore_dict.items() if doc_data.metadata.get("document_id") == document_id]
            if ids_to_delete:
                vectorstore.delete(ids_to_delete)
                vectorstore.save_local(index_path)
    except Exception as e:
        print(f"Failed to delete embeddings for document {document_id}: {e}")
        
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}

@router.post("/{document_id}/reindex", response_model=schemas.DocumentResponse)
def reindex_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    doc = db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.tenant_id == current_user.tenant_id
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = "Processing"
    doc.progress = 0.05
    doc.error_message = None
    db.commit()
    db.refresh(doc)

    if os.getenv("CELERY_BROKER_URL"):
        from ingestion.task_queue import reindex_document_task
        task = reindex_document_task.delay(doc.id, current_user.tenant_id)
        doc.celery_task_id = task.id
        db.commit()
    else:
        background_tasks.add_task(reembed_stored_chunks, doc.id, current_user.tenant_id, db)

    return doc

@router.get("/{document_id}/chunks")
def get_document_chunks(
    document_id: int,
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    doc = db.query(models.Document).filter(
        models.Document.id == document_id, 
        models.Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    db_chunks = db.query(models.DocumentChunk).filter(
        models.DocumentChunk.document_id == document_id
    ).order_by(models.DocumentChunk.chunk_index).all()
    
    return {"chunks": [schemas.DocumentChunkResponse.model_validate(c) for c in db_chunks]}

@router.post("/search", response_model=schemas.SearchSynthesisResponse)
def search_documents(
    query: schemas.SearchQuery,
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    try:
        global embeddings_model
        if embeddings_model is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
        index_path = f"vector_store/tenant_{current_user.tenant_id}"
        if not os.path.exists(index_path):
             return {
                 "query": query.query,
                 "answer": "No indexed documents found for your tenant. Please upload documents first.",
                 "results": []
             }

        import numpy as np
        from langchain_community.vectorstores import FAISS
        vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
        
        # 1. Dense FAISS Search
        embedding = embeddings_model.embed_query(query.query)
        scores, indices = vectorstore.index.search(np.array([embedding], dtype=np.float32), 50)
        
        dense_results = []
        for score, i in zip(scores[0], indices[0]):
            if i == -1: continue
            try:
                _id = vectorstore.index_to_docstore_id[int(i)]
                doc = vectorstore.docstore.search(_id)
                meta = doc.metadata or {}
                
                # Apply metadata filters
                if query.document_ids and meta.get("document_id") not in query.document_ids:
                    continue
                if query.content_types and meta.get("content_type") not in query.content_types:
                    continue
                if query.page_range and len(query.page_range) == 2:
                    p_num = meta.get("page_number")
                    if p_num and not (query.page_range[0] <= p_num <= query.page_range[1]):
                        continue
                        
                dense_results.append({
                    "content": doc.page_content,
                    "metadata": meta,
                    "score": float(score)
                })
            except KeyError:
                continue

        # 2. Sparse BM25 Search
        sparse_results = []
        if query.search_mode != "semantic":
            bm25_manager = BM25IndexManager(tenant_id=current_user.tenant_id)
            bm25_hits = bm25_manager.search(query.query, top_k=50)
            
            for hit in bm25_hits:
                chunk_obj = db.query(models.DocumentChunk).filter(models.DocumentChunk.id == hit["chunk_id"]).first()
                if chunk_obj:
                    meta = hit["metadata"]
                    if query.document_ids and meta.get("document_id") not in query.document_ids:
                        continue
                    if query.content_types and meta.get("content_type") not in query.content_types:
                        continue
                    if query.page_range and len(query.page_range) == 2:
                        p_num = meta.get("page_number")
                        if p_num and not (query.page_range[0] <= p_num <= query.page_range[1]):
                            continue
                    sparse_results.append({
                        "content": chunk_obj.content,
                        "metadata": meta,
                        "score": hit["score"]
                    })

        # 3. Reciprocal Rank Fusion (RRF)
        top_k = query.top_k or 5
        fusion_top_k = top_k * 4 if query.re_rank else top_k
        top_results = reciprocal_rank_fusion(dense_results, sparse_results, k=60, top_k=fusion_top_k)

        if query.re_rank and top_results:
            top_results = cross_encoder_rerank(query.query, top_results, top_k=top_k)

        if not top_results:
            return {
                "query": query.query,
                "answer": "No relevant document chunks found in your knowledge base matching your filter criteria.",
                "results": []
            }

        answer = None
        if query.synthesize:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if gemini_api_key:
                try:
                    import requests
                    context_parts = []
                    for idx, r in enumerate(top_results, 1):
                        filename = r.get("metadata", {}).get("source", f"Document_{idx}")
                        content = r.get("content", "").strip()
                        context_parts.append(f"[Document Chunk #{idx} - Source: {filename}]\n{content}")
                    context_text = "\n\n".join(context_parts)

                    prompt = (
                        "You are an expert AI assistant for a RAG Knowledge Base.\n"
                        "Based strictly on the document context provided below, synthesize a concise, clear, and comprehensive natural language answer to the user's question.\n"
                        "IMPORTANT CITATION RULE: Always include inline citations in the format [Source: filename] whenever referencing facts, figures, or details from a document chunk.\n\n"
                        f"User Question: {query.query}\n\n"
                        f"Document Context:\n{context_text}"
                    )

                    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_api_key}"
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    headers = {"Content-Type": "application/json"}
                    res = requests.post(gemini_url, json=payload, headers=headers, timeout=30)
                    if res.status_code == 200:
                        res_data = res.json()
                        answer = res_data["candidates"][0]["content"]["parts"][0]["text"]
                except Exception as err:
                    print(f"Gemini synthesis error: {err}")

            if not answer:
                summary_items = [f"- {r.get('content', '')[:180]}... [Source: {r.get('metadata', {}).get('source', 'doc')}]" for r in top_results[:3]]
                answer = f"Synthesized summary from {len(top_results)} matching document chunk(s):\n" + "\n".join(summary_items)

        return {
            "query": query.query,
            "answer": answer,
            "results": top_results
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

