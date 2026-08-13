#!/usr/bin/env python3
"""
DataSpeakAI — Embedding Model Migration Script

Iterates all tenants, re-embeds stored DocumentChunk records using a target embedding model
(default: 'BAAI/bge-small-en-v1.5'), rebuilds FAISS dense & BM25 sparse indices, and updates
the Document.embedding_model field in the database.

Usage:
  python backend/scripts/migrate_embeddings.py [--model BAAI/bge-small-en-v1.5] [--dry-run]
"""

import os
import sys
import argparse
import logging

# Ensure backend root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database import SessionLocal
import models
from search.bm25_index import BM25IndexManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def migrate_tenant_embeddings(tenant_id: int, target_model: str, dry_run: bool, db):
    """
    Migrates FAISS & BM25 indices for a given tenant using target embedding model.
    """
    tenant_docs = db.query(models.Document).filter(models.Document.tenant_id == tenant_id).all()
    if not tenant_docs:
        logger.info(f"Tenant {tenant_id}: No documents found. Skipping.")
        return

    doc_ids = [d.id for d in tenant_docs]
    tenant_chunks = db.query(models.DocumentChunk).filter(
        models.DocumentChunk.document_id.in_(doc_ids)
    ).order_by(models.DocumentChunk.document_id, models.DocumentChunk.chunk_index).all()

    if not tenant_chunks:
        logger.info(f"Tenant {tenant_id}: Found {len(tenant_docs)} documents but 0 chunks. Skipping.")
        return

    logger.info(f"Tenant {tenant_id}: Found {len(tenant_docs)} documents, {len(tenant_chunks)} total chunks.")

    if dry_run:
        logger.info(f"[DRY-RUN] Would re-embed {len(tenant_chunks)} chunks for Tenant {tenant_id} using model '{target_model}'.")
        for doc in tenant_docs:
            logger.info(f"[DRY-RUN] Would update Document {doc.id} ('{doc.name}') embedding_model -> '{target_model}'")
        return

    # Load new embedding model
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    
    logger.info(f"Loading embedding model '{target_model}'...")
    embeddings_model = HuggingFaceEmbeddings(model_name=target_model)

    index_dir = f"vector_store/tenant_{tenant_id}"
    index_file = os.path.join(index_dir, "index.faiss")
    index_pkl = os.path.join(index_dir, "index.pkl")

    # Clear old FAISS index files if they exist
    if os.path.exists(index_file):
        os.remove(index_file)
    if os.path.exists(index_pkl):
        os.remove(index_pkl)

    # Gather all chunk texts & metadata
    all_texts = []
    all_metadatas = []
    
    doc_map = {d.id: d for d in tenant_docs}

    for c in tenant_chunks:
        doc = doc_map.get(c.document_id)
        doc_name = doc.name if doc else ""
        all_texts.append(c.content)
        all_metadatas.append({
            "document_id": c.document_id,
            "source": doc_name,
            "page_number": c.page_number,
            "content_type": c.content_type,
            "section_heading": c.section_heading,
            "reference_id": c.reference_id
        })

    logger.info(f"Generating FAISS embeddings for {len(all_texts)} chunks...")
    vectorstore = FAISS.from_texts(texts=all_texts, embedding=embeddings_model, metadatas=all_metadatas)
    os.makedirs(index_dir, exist_ok=True)
    vectorstore.save_local(index_dir)
    logger.info(f"Saved new FAISS index to {index_dir}")

    # Rebuild BM25 index
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
                "source": doc_map.get(c.document_id, models.Document()).name
            }
        } for c in tenant_chunks
    ]
    bm25_manager = BM25IndexManager(tenant_id=tenant_id)
    bm25_manager.build_index(bm25_input)
    logger.info(f"Rebuilt BM25 index for Tenant {tenant_id}")

    # Update database records
    for doc in tenant_docs:
        doc.embedding_model = target_model
    db.commit()
    logger.info(f"Updated {len(tenant_docs)} documents' embedding_model field in database.")

def main():
    parser = argparse.ArgumentParser(description="DataSpeakAI Embedding Model Migration Script")
    parser.add_argument("--model", type=str, default="BAAI/bge-small-en-v1.5", help="Target HuggingFace embedding model")
    parser.add_argument("--dry-run", action="store_true", help="Simulate migration without modifying FAISS index or DB")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        tenants = db.query(models.Tenant).all()
        logger.info(f"Starting migration check across {len(tenants)} tenant(s). Target Model: '{args.model}' (Dry-run: {args.dry_run})")
        for tenant in tenants:
            migrate_tenant_embeddings(tenant.id, args.model, args.dry_run, db)
        logger.info("Embedding migration complete!")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    main()
