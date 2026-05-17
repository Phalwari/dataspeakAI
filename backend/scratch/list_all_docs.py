import sys
sys.path.append('.')
from database import SessionLocal
import models

db = SessionLocal()
try:
    docs = db.query(models.Document).all()
    print("--- ALL DOCUMENTS IN SQLITE ---")
    for doc in docs:
        chunks = db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == doc.id).all()
        print(f"ID: {doc.id}, Name: {doc.name}, Tenant: {doc.tenant_id}, Status: {doc.status}, Chunks: {len(chunks)}, Tables: {doc.table_count}, Images: {doc.image_count}")
finally:
    db.close()
