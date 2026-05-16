import os
import shutil
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from routers.documents import process_document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def setup_test_data():
    db = SessionLocal()
    # Create a test tenant if not exists
    tenant = db.query(models.Tenant).filter(models.Tenant.name == "Test Tenant").first()
    if not tenant:
        tenant = models.Tenant(name="Test Tenant")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    
    # Create a test document entry
    doc = models.Document(
        tenant_id=tenant.id,
        name="test_rag_file.txt",
        file_type="TXT",
        size=0,
        status="Processing",
        embeddings_count=0
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # Create a test file
    os.makedirs("uploads", exist_ok=True)
    file_path = "uploads/test_rag_file.txt"
    content = "This is a test file for RAG. " * 100 # Large enough for multiple chunks
    with open(file_path, "w") as f:
        f.write(content)
        
    doc.size = len(content)
    db.commit()
    
    return db, tenant, doc, file_path

def test_processing():
    db, tenant, doc, file_path = setup_test_data()
    print(f"Testing processing for Document ID: {doc.id}, Tenant ID: {tenant.id}")
    
    # Run the processing logic
    process_document(doc.id, file_path, tenant.id, db)
    
    # Refresh and check results
    db.refresh(doc)
    print(f"Status: {doc.status}")
    print(f"Embeddings Count: {doc.embeddings_count}")
    
    if doc.status == "Completed" and doc.embeddings_count > 0:
        print("SUCCESS: Document processed and indexed.")
        
        # Verify FAISS index exists
        index_path = f"vector_store/tenant_{tenant.id}"
        if os.path.exists(index_path):
            print(f"SUCCESS: Vector store created at {index_path}")
            
            # Test retrieval from the real index
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
            results = vectorstore.similarity_search("test file", k=1)
            print(f"Retrieval Test: {results[0].page_content[:100]}...")
        else:
            print("FAILURE: Vector store index path not found.")
    else:
        print("FAILURE: Processing did not complete as expected.")

    # Cleanup
    # db.delete(doc)
    # db.commit()
    # if os.path.exists(file_path):
    #     os.remove(file_path)

if __name__ == "__main__":
    try:
        test_processing()
    except Exception as e:
        print(f"Test failed with error: {e}")
