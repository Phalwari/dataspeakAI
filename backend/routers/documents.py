from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.orm import Session, joinedload
from typing import Tuple, List, Optional, Dict, Any
from datetime import datetime
import re
import hashlib
import models, schemas
from database import get_db, SessionLocal
from dependencies import get_current_user, require_source_manager, require_query_executor
import os
import io

# Move heavy imports inside functions to prevent OOM on startup
has_ai_libs = True 

router = APIRouter(prefix="/api/documents", tags=["documents"])

os.makedirs("uploads", exist_ok=True)
os.makedirs("vector_store", exist_ok=True)

# We use a global variable fallback for test doubles/monkeypatching
embeddings_model = None

def _load_hf_embeddings(model_name="all-MiniLM-L6-v2"):
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=model_name)

def resolve_tenant_vector_index_path(tenant_id: int, model_name: str = "all-MiniLM-L6-v2") -> Tuple[str, bool]:
    """
    Resolves the active FAISS vector store path for a tenant.
    Returns (path, exists).
    Checks active generation pointer first (NR-2.2-B-T07), then versioned directory, then legacy un-slugged path.
    """
    from search.generation_manager import IndexGenerationManager
    gen_mgr = IndexGenerationManager(tenant_id, model_name)
    active_path, active_exists = gen_mgr.get_active_generation_path()
    if active_exists:
        return active_path, True

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

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB Limit (NR-2.2-B-T02)

def process_document(document_id: int, file_path: str, tenant_id: int, chunk_size: int = 512, chunk_overlap: int = 50, strategy: str = "fixed", db: Optional[Session] = None):
    close_db = False
    if db is None:
        from database import SessionLocal
        db = SessionLocal()
        close_db = True

    doc = db.query(models.Document).filter(models.Document.id == document_id, models.Document.tenant_id == tenant_id, models.Document.is_deleted == False).first()
    if not doc:
        if close_db:
            db.close()
        return

    try:
        # Assign job ID and initial step (NR-2.2-B-T03)
        if not doc.ingestion_job_id:
            doc.ingestion_job_id = str(uuid.uuid4())
        doc.progress_step = "parsing"
        doc.status = "Processing"
        doc.progress = 0.1
        doc.last_heartbeat_at = datetime.utcnow()
        db.commit()

        gemini_api_key = os.getenv("GEMINI_API_KEY")
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".bin" or not ext:
            if doc and doc.name:
                ext = os.path.splitext(doc.name)[1].lower()
            elif doc and doc.file_type:
                ext = f".{doc.file_type.lower()}"
        
        # 1. Extract content based on file extension
        if ext == '.pdf':
            extracted = extract_pdf_split_router(file_path, gemini_api_key)
        elif ext == '.docx':
            extracted = extract_docx(file_path)
        elif ext in ['.xlsx', '.xls', '.csv']:
            extracted = extract_excel_csv(file_path, file_ext=ext)
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
        doc.pages_processed = extracted.stats.pages_processed
        doc.visual_pages = extracted.stats.visual_pages
        doc.table_count = extracted.stats.table_count
        doc.image_count = extracted.stats.image_count
        doc.progress_step = "chunking"
        doc.progress = 0.3
        doc.last_heartbeat_at = datetime.utcnow()
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

        # Purge pre-existing chunks for this document to avoid duplication on retry (F03)
        db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == document_id).delete()
        db.flush()

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

        doc.progress_step = "indexing"
        doc.progress = 0.6
        doc.last_heartbeat_at = datetime.utcnow()
        db.commit()

        # 5. Index Chunks into Immutable Generation (Task NR-2.2-B-T07)
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

        model_name = getattr(doc, "embedding_model", "all-MiniLM-L6-v2") or "all-MiniLM-L6-v2"
        # Support test doubles if monkeypatched on module, else load clean instance
        active_embeddings = embeddings_model if embeddings_model is not None else _load_hf_embeddings(model_name)

        # Build BM25 input for tenant (strictly active, non-deleted chunks - NR-2.2-B-T05 / Defect I-12)
        all_tenant_chunks = db.query(models.DocumentChunk).options(
            joinedload(models.DocumentChunk.document)
        ).join(models.Document).filter(
            models.Document.tenant_id == tenant_id,
            models.Document.status == "Completed",
            models.Document.is_deleted == False
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
        # Include current document's newly flushed chunks into BM25
        for db_c in target_db_objs:
            bm25_input.append({
                "id": db_c.id,
                "content": db_c.content,
                "metadata": {
                    "document_id": document_id,
                    "chunk_index": db_c.chunk_index,
                    "page_number": db_c.page_number,
                    "content_type": db_c.content_type,
                    "reference_id": db_c.reference_id,
                    "source": doc.name
                }
            })

        from search.generation_manager import IndexGenerationManager
        gen_mgr = IndexGenerationManager(tenant_id=tenant_id, model_name=model_name)
        gen_mgr.build_and_publish_generation(
            embeddings_model=active_embeddings,
            new_chunks=all_chunks,
            new_metadatas=all_metadatas,
            all_bm25_chunks=bm25_input,
            live_document_ids=lambda: {row.id for row in db.query(models.Document.id).filter(
                models.Document.tenant_id == tenant_id, models.Document.is_deleted == False).all()},
        )

        doc.status = "Completed"
        doc.progress_step = "ready"
        doc.embeddings_count = len(all_chunks)
        doc.pages_processed = extracted.stats.pages_processed
        doc.progress = 1.0
        doc.last_heartbeat_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        db.rollback()
        doc.status = "Failed"
        doc.progress_step = "failed"
        doc.error_message = str(e)
        doc.progress = 0.0
        doc.last_heartbeat_at = datetime.utcnow()
        db.commit()
        raise

    finally:
        # The durable source must survive transient failures and worker retries.
        if close_db:
            db.close()

def reembed_stored_chunks(document_id: int, tenant_id: int, db: Session = None):
    close_db = False
    if db is None:
        from database import SessionLocal
        db = SessionLocal()
        close_db = True

    try:
        doc = db.query(models.Document).filter(models.Document.id == document_id, models.Document.tenant_id == tenant_id, models.Document.is_deleted == False).first()
        if not doc:
            return

        doc.status = "Processing"
        doc.progress = 0.1
        db.commit()

        model_name = getattr(doc, "embedding_model", "all-MiniLM-L6-v2") or "all-MiniLM-L6-v2"
        active_embeddings = embeddings_model
        if active_embeddings is None or getattr(active_embeddings, "model_name", None) != model_name:
            active_embeddings = _load_hf_embeddings(model_name)

        db_chunks = db.query(models.DocumentChunk).filter(
            models.DocumentChunk.document_id == document_id
        ).order_by(models.DocumentChunk.chunk_index).all()

        all_chunks = []
        all_metadatas = []
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

        doc.progress = 0.5
        db.commit()

        # Build BM25 input for tenant (strictly active, non-deleted chunks)
        all_tenant_chunks = db.query(models.DocumentChunk).options(
            joinedload(models.DocumentChunk.document)
        ).join(models.Document).filter(
            models.Document.tenant_id == tenant_id,
            models.Document.status == "Completed",
            models.Document.is_deleted == False
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

        from search.generation_manager import IndexGenerationManager
        gen_mgr = IndexGenerationManager(tenant_id=tenant_id, model_name=model_name)
        gen_mgr.build_and_publish_generation(
            embeddings_model=active_embeddings,
            new_chunks=all_chunks,
            new_metadatas=all_metadatas,
            all_bm25_chunks=bm25_input,
            live_document_ids=lambda: {row.id for row in db.query(models.Document.id).filter(
                models.Document.tenant_id == tenant_id, models.Document.is_deleted == False).all()},
        )

        doc.status = "Completed"
        doc.embeddings_count = len(db_chunks)
        doc.progress = 1.0
        doc.error_message = None
        db.commit()

    except Exception as e:
        db.rollback()
        doc.status = "Failed"
        doc.error_message = str(e)
        doc.progress = 0.0
        db.commit()
        raise
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
        
    return db.query(models.Document).filter(
        models.Document.tenant_id == current_user.tenant_id,
        models.Document.is_deleted == False
    ).all()

@router.get("/{document_id}/status", response_model=schemas.DocumentStatusResponse)
def get_document_status(
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
        
    return schemas.DocumentStatusResponse(
        document_id=doc.id,
        id=doc.id,
        name=doc.name,
        status=doc.status,
        progress=doc.progress or 0.0,
        progress_step=doc.progress_step or "queued",
        ingestion_job_id=doc.ingestion_job_id,
        error_message=doc.error_message,
        pages_processed=doc.pages_processed or 0,
        total_pages=doc.total_pages or 0,
        last_heartbeat_at=doc.last_heartbeat_at
    )

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

    from ingestion.extractors import validate_file_magic
    from services.storage import storage_service

    # Streaming file read with 25MB size limit check and magic signature inspection (NR-2.2-B-T02)
    file_size = 0
    safe_filename = os.path.basename(file.filename or "uploaded_document")
    unique_filename = f"{uuid.uuid4()}_{safe_filename}"
    file_path = f"uploads/{unique_filename}"
    sha256 = hashlib.sha256()
    first_chunk = True

    try:
        with open(file_path, "wb") as f:
            while chunk := await file.read(8192):
                if first_chunk:
                    is_valid, reason = validate_file_magic(chunk, safe_filename)
                    if not is_valid:
                        f.close()
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"File validation failed: {reason}"
                        )
                    first_chunk = False

                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    f.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File exceeds maximum allowed size of 25MB"
                    )
                sha256.update(chunk)
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as read_err:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Failed to read upload stream: {read_err}")

    content_hash = sha256.hexdigest()
    ext = os.path.splitext(safe_filename)[1].upper().replace('.', '') or "TXT"
    job_id = str(uuid.uuid4())

    doc = models.Document(
        tenant_id=current_user.tenant_id,
        name=safe_filename,
        file_type=ext,
        size=file_size,
        status="Processing",
        progress_step="queued",
        ingestion_job_id=job_id,
        content_sha256=content_hash,
        version=1,
        embeddings_count=0,
        progress=0.05,
        last_heartbeat_at=datetime.utcnow(),
        is_deleted=False
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Store uploaded original under durable, content-addressed storage key (NR-2.2-B-T01)
    stored_path = storage_service.store_file(current_user.tenant_id, doc.id, file_path, content_hash, filename=safe_filename)
    doc.storage_key = stored_path
    if os.path.abspath(file_path) != os.path.abspath(stored_path):
        os.remove(file_path)
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
        task = process_document_task.delay(doc.id, stored_path, current_user.tenant_id, chunk_size, chunk_overlap, chunking_strategy)
        doc.celery_task_id = task.id
        db.commit()
    else:
        background_tasks.add_task(process_document, doc.id, stored_path, current_user.tenant_id, chunk_size, chunk_overlap, chunking_strategy)
    
    return doc

@router.post("/{document_id}/retry", response_model=schemas.DocumentResponse)
def retry_document_ingestion(
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
    if doc.is_deleted:
        raise HTTPException(status_code=400, detail="Cannot retry a deleted document")

    from services.storage import storage_service
    file_to_process = None
    if doc.content_sha256:
        stored_path = storage_service.get_file_path(current_user.tenant_id, doc.id, doc.content_sha256, filename=doc.name)
        if stored_path and os.path.exists(stored_path):
            file_to_process = stored_path

    if not file_to_process and doc.storage_key and os.path.exists(doc.storage_key):
        file_to_process = doc.storage_key

    if not file_to_process:
        raise HTTPException(status_code=400, detail="Original document file not found in storage. Please re-upload.")

    doc.status = "Processing"
    doc.progress_step = "queued"
    doc.error_message = None
    doc.progress = 0.05
    doc.last_heartbeat_at = datetime.utcnow()
    doc.ingestion_job_id = str(uuid.uuid4())
    db.commit()
    db.refresh(doc)

    if os.getenv("CELERY_BROKER_URL"):
        from ingestion.task_queue import process_document_task
        task = process_document_task.delay(doc.id, file_to_process, current_user.tenant_id, 512, 50, "fixed")
        doc.celery_task_id = task.id
        db.commit()
    else:
        background_tasks.add_task(process_document, doc.id, file_to_process, current_user.tenant_id, 512, 50, "fixed")
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
        
    # Immediate tombstoning (NR-2.2-B-T08 / Defect I-12)
    doc.is_deleted = True
    doc.status = "Deleted"
    doc.progress_step = "deleted"
    db.commit()

    # Purge chunk rows and widget key associations from database (F07)
    db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == document_id).delete()
    db.query(models.WidgetKeyDocument).filter(models.WidgetKeyDocument.document_id == document_id).delete()
    db.commit()

    try:
        model_name = getattr(doc, "embedding_model", "all-MiniLM-L6-v2") or "all-MiniLM-L6-v2"
        emb = embeddings_model if embeddings_model is not None else _load_hf_embeddings(model_name)
        index_path, exists = resolve_tenant_vector_index_path(current_user.tenant_id, model_name)
        if exists and os.path.exists(index_path):
            from langchain_community.vectorstores import FAISS
            vectorstore = FAISS.load_local(index_path, emb, allow_dangerous_deserialization=True)
            docstore_dict = vectorstore.docstore._dict
            ids_to_delete = [uid for uid, doc_data in docstore_dict.items() if doc_data.metadata.get("document_id") == document_id]
            if ids_to_delete:
                vectorstore.delete(ids_to_delete)
                vectorstore.save_local(index_path)
    except Exception as e:
        print(f"Failed to delete embeddings for document {document_id}: {e}")

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
        # Pre-fetch active completed, non-deleted document IDs for tenant to eliminate N+1 query loop (F09)
        active_doc_ids = set(
            d[0] for d in db.query(models.Document.id).filter(
                models.Document.tenant_id == current_user.tenant_id,
                models.Document.status == "Completed",
                models.Document.is_deleted == False
            ).all()
        )

        scores, indices = vectorstore.index.search(query_arr, 50)
        for score, i in zip(scores[0], indices[0]):
            if i == -1: continue
            try:
                _id = vectorstore.index_to_docstore_id[int(i)]
                doc = vectorstore.docstore.search(_id)
                meta = doc.metadata or {}
                
                # Check for active, non-deleted parent document (NR-2.2-B-T08 / F09)
                doc_id = meta.get("document_id")
                if doc_id and doc_id not in active_doc_ids:
                    continue

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

        # 2. Sparse BM25 Search (using active generation path if present - F04)
        sparse_results = []
        if query.search_mode != "semantic":
            active_bm25_dir = index_path if os.path.exists(os.path.join(index_path, "bm25.pkl")) else None
            bm25_manager = BM25IndexManager(tenant_id=current_user.tenant_id, index_dir=active_bm25_dir)
            bm25_hits = bm25_manager.search(query.query, top_k=50)
            
            if bm25_hits:
                bm25_chunk_ids = [hit["chunk_id"] for hit in bm25_hits]
                chunk_map = {
                    c.id: c for c in db.query(models.DocumentChunk).filter(
                        models.DocumentChunk.id.in_(bm25_chunk_ids),
                        models.DocumentChunk.document_id.in_(active_doc_ids)
                    ).all()
                }
                for hit in bm25_hits:
                    chunk_obj = chunk_map.get(hit["chunk_id"])
                    if not chunk_obj:
                        continue

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

                    from services.llm_generation_service import llm_gateway
                    raw = llm_gateway.generate_sync(
                        prompt=prompt,
                        tenant_id=current_user.tenant_id,
                        purpose="document_search"
                    )
                    if raw and not raw.startswith("Sorry, all AI providers"):
                        answer = raw.strip()
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

