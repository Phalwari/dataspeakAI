import sys
sys.path.append('.')
import os
import sqlite3
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from routers.documents import process_document
from dotenv import load_dotenv

load_dotenv()

# Clear existing document entries for a clean run
db = SessionLocal()
try:
    existing_doc = db.query(models.Document).filter(models.Document.name == "rag_test_document.pdf").first()
    if existing_doc:
        print(f"Clearing old entries for document {existing_doc.id}")
        db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == existing_doc.id).delete()
        db.delete(existing_doc)
        db.commit()
        
    # Create a fresh mock document entry in SQLite
    doc = models.Document(
        tenant_id=1,
        name="rag_test_document.pdf",
        file_type="PDF",
        size=4469,
        status="Processing",
        embeddings_count=0
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    print(f"Created mock document ID {doc.id}. Starting process_document...")
    
    # Process the document
    process_document(
        document_id=doc.id,
        file_path="uploads/rag_test_document.pdf",
        tenant_id=1,
        chunk_size=512,
        chunk_overlap=50,
        strategy="fixed",
        db=db
    )
    
    # Reload and inspect document details
    db.refresh(doc)
    print(f"\nIngestion Completed! Status: {doc.status}")
    print(f"Total Chunks Generated: {doc.embeddings_count}")
    print(f"Total Sentences: {doc.line_count}")
    print(f"Table Count: {doc.table_count}")
    print(f"Image Count: {doc.image_count}")
    
    # Print all chunks from relational SQLite database
    chunks = db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == doc.id).all()
    print("\n" + "="*50)
    print("ALL GENERATED CHUNKS FROM SQLITE")
    print("="*50)
    for chunk in chunks:
        print(f"\n--- Chunk #{chunk.chunk_index + 1} ---")
        print(chunk.content)
        print("-"*50)
        
finally:
    db.close()
