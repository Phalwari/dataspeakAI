from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import Tuple, List, Optional, Dict, Any
import re
import models, schemas
from database import get_db
from dependencies import get_current_user, require_source_manager, require_query_executor
import os
import io

# Move heavy imports inside functions to prevent OOM on startup
has_ai_libs = True 

router = APIRouter(prefix="/api/documents", tags=["documents"])

os.makedirs("uploads", exist_ok=True)
os.makedirs("vector_store", exist_ok=True)

# We use a global variable to load embeddings once
embeddings_model = None

def _load_hf_embeddings(model_name="all-MiniLM-L6-v2"):
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=model_name)

def resolve_tenant_vector_index_path(tenant_id: int, model_name: str = "all-MiniLM-L6-v2") -> Tuple[str, bool]:
    """
    Resolves the versioned FAISS vector store path for a tenant.
    Returns (path, exists).
    Falls back to legacy un-slugged path if versioned directory does not exist.
    """
    clean_model = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', model_name or "all-MiniLM-L6-v2").strip("._")
    model_slug = clean_model or "all-MiniLM-L6-v2"
    versioned_path = f"vector_store/tenant_{tenant_id}_{model_slug}"
    legacy_path = f"vector_store/tenant_{tenant_id}"

    if os.path.exists(versioned_path):
        return versioned_path, True
    if os.path.exists(legacy_path):
        return legacy_path, True
    return versioned_path, False


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

        # 2. Hierarchical Chunking (Task 7.2.2)
        from ingestion.semantic_chunker import SemanticHierarchicalChunker
        chunker = SemanticHierarchicalChunker(
            target_chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        parent_specs, child_specs = chunker.chunk_extracted_content(
            extracted_content=extracted,
            document_id=document_id,
            document_name=doc.name
        )

        # 3. Persist Level 0 Parent Chunks to SQL table
        parent_db_objs = []
        for i, p in enumerate(parent_specs):
            db_p = models.DocumentChunk(
                document_id=document_id,
                content=p.content,
                overlap_chars=0,
                chunk_index=i,
                page_number=p.page_number,
                content_type=p.content_type,
                section_heading=p.section_heading,
                reference_id=p.reference_id,
                parent_chunk_id=None,
                hierarchy_level=0
            )
            db.add(db_p)
            parent_db_objs.append(db_p)
        db.flush()

        # 4. Persist Level 1 Child Chunks to SQL table (linked to parent_chunk_id)
        child_db_objs = []
        for j, c in enumerate(child_specs):
            parent_id = None
            if c.parent_local_index is not None and c.parent_local_index < len(parent_db_objs):
                parent_id = parent_db_objs[c.parent_local_index].id

            db_c = models.DocumentChunk(
                document_id=document_id,
                content=c.content,
                overlap_chars=chunk_overlap,
                chunk_index=len(parent_specs) + j,
                page_number=c.page_number,
                content_type=c.content_type,
                section_heading=c.section_heading,
                reference_id=c.reference_id,
                parent_chunk_id=parent_id,
                hierarchy_level=1
            )
            db.add(db_c)
            child_db_objs.append(db_c)
        db.flush()

        doc.progress = 0.6
        db.commit()

        # 5. Index Child Chunks into Versioned FAISS (Task 7.2.4)
        target_specs = child_specs if child_specs else parent_specs
        target_db_objs = child_db_objs if child_specs else parent_db_objs

        all_chunks = [s.content for s in target_specs]
        all_metadatas = []
        for s, db_chunk in zip(target_specs, target_db_objs):
            meta = dict(s.metadata)
            meta["chunk_id"] = db_chunk.id
            meta["parent_chunk_id"] = db_chunk.parent_chunk_id
            meta["document_id"] = document_id
            meta["source"] = doc.name
            all_metadatas.append(meta)

        global embeddings_model
        model_name = getattr(doc, "embedding_model", "all-MiniLM-L6-v2") or "all-MiniLM-L6-v2"
        if embeddings_model is None or getattr(embeddings_model, "model_name", None) != model_name:
            embeddings_model = _load_hf_embeddings(model_name)

        model_slug = model_name.replace("/", "_").replace(":", "_")
        versioned_index_path = f"vector_store/tenant_{tenant_id}_{model_slug}"
        legacy_index_path = f"vector_store/tenant_{tenant_id}"

        index_load_path = versioned_index_path
        if not os.path.exists(versioned_index_path) and os.path.exists(legacy_index_path):
            index_load_path = legacy_index_path

        from langchain_community.vectorstores import FAISS
        if os.path.exists(index_load_path):
            vectorstore = FAISS.load_local(index_load_path, embeddings_model, allow_dangerous_deserialization=True)
            vectorstore.add_texts(texts=all_chunks, metadatas=all_metadatas)
        else:
            vectorstore = FAISS.from_texts(texts=all_chunks, embedding=embeddings_model, metadatas=all_metadatas)

        os.makedirs("vector_store", exist_ok=True)
        vectorstore.save_local(versioned_index_path)

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
                    "source": c.document.name if (hasattr(c, "document") and c.document) else doc.name
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
        model_name = getattr(doc, "embedding_model", "all-MiniLM-L6-v2") or "all-MiniLM-L6-v2"
        if embeddings_model is None or getattr(embeddings_model, "model_name", None) != model_name:
            embeddings_model = _load_hf_embeddings(model_name)

        model_slug = model_name.replace("/", "_").replace(":", "_")
        versioned_index_path = f"vector_store/tenant_{tenant_id}_{model_slug}"
        index_path, exists = resolve_tenant_vector_index_path(tenant_id, model_name)
        if not exists:
            index_path = versioned_index_path

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
                "chunk_id": c.id,
                "document_id": document_id,
                "parent_chunk_id": c.parent_chunk_id,
                "hierarchy_level": c.hierarchy_level,
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

            os.makedirs("vector_store", exist_ok=True)
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
                    "source": c.document.name if (hasattr(c, "document") and c.document) else doc.name
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
    current_user: models.User = Depends(require_source_manager), 
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

    # Auto-publish newly uploaded document to all active widget keys in the tenant (Grill-Me decision)
    active_widget_keys = db.query(models.WidgetKey).filter(
        models.WidgetKey.tenant_id == current_user.tenant_id,
        models.WidgetKey.enabled == True
    ).all()
    for wk in active_widget_keys:
        assoc = models.WidgetKeyDocument(
            widget_key_id=wk.id,
            document_id=doc.id
        )
        db.add(assoc)
    if active_widget_keys:
        db.commit()
    
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
    current_user: models.User = Depends(require_source_manager), 
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
        model_name = getattr(doc, "embedding_model", "all-MiniLM-L6-v2") or "all-MiniLM-L6-v2"
        if embeddings_model is None or getattr(embeddings_model, "model_name", None) != model_name:
            embeddings_model = _load_hf_embeddings(model_name)
        
        index_path, exists = resolve_tenant_vector_index_path(current_user.tenant_id, model_name)
        if exists and os.path.exists(index_path):
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
    current_user: models.User = Depends(require_source_manager),
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
    current_user: models.User = Depends(require_query_executor), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    # Strict Tenant Scoping: Verify any requested document_ids strictly belong to current tenant
    if query.document_ids:
        valid_doc_count = db.query(models.Document.id).filter(
            models.Document.id.in_(query.document_ids),
            models.Document.tenant_id == current_user.tenant_id
        ).count()
        if valid_doc_count != len(set(query.document_ids)):
            raise HTTPException(status_code=404, detail="Document not found")
        
    try:
        global embeddings_model
        if embeddings_model is None:
            embeddings_model = _load_hf_embeddings("all-MiniLM-L6-v2")
            
        index_path, exists = resolve_tenant_vector_index_path(current_user.tenant_id, "all-MiniLM-L6-v2")
        if not exists:
             return {
                 "query": query.query,
                 "answer": "No indexed documents found for your tenant. Please upload documents first.",
                 "results": []
             }

        import numpy as np
        from langchain_community.vectorstores import FAISS
        vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
        
        # 1. Dense FAISS Search with Dimension Safety Guard (Task 7.2.4)
        embedding = embeddings_model.embed_query(query.query)
        query_arr = np.array([embedding], dtype=np.float32)

        dense_results = []
        expected_dim = getattr(vectorstore.index, "d", 384)
        if query_arr.shape[1] != expected_dim:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vector dimension mismatch: query embedding has dimension {query_arr.shape[1]} but index expects {expected_dim}. Please re-index documents with the matching model."
            )
        scores, indices = vectorstore.index.search(query_arr, 50)
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

