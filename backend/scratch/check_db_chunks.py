import sys
sys.path.append('.')
from database import SessionLocal
import models

db = SessionLocal()
try:
    docs = db.query(models.Document).order_by(models.Document.id.desc()).all()
    print("--- RECENT DOCUMENTS IN SQLITE ---")
    for doc in docs[:5]:
        print(f"ID: {doc.id}, Name: {doc.name}, Tenant: {doc.tenant_id}, Status: {doc.status}, Chunks: {doc.embeddings_count}, Tables: {doc.table_count}, Images: {doc.image_count}")
        chunks = db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == doc.id).all()
        print(f"  Saved Chunks ({len(chunks)}):")
        for chunk in chunks:
            print(f"    - Index {chunk.chunk_index} (Len={len(chunk.content)}): {chunk.content[:60]}...")
finally:
    db.close()
