from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
import models, schemas
from database import get_db
from dependencies import get_current_user
import os
import io

try:
    from pypdf import PdfReader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    has_ai_libs = True
except ImportError:
    has_ai_libs = False

router = APIRouter(prefix="/api/documents", tags=["documents"])

os.makedirs("uploads", exist_ok=True)
os.makedirs("vector_store", exist_ok=True)

# We use a global variable to load embeddings once
embeddings_model = None

def process_document(document_id: int, file_path: str, tenant_id: int, chunk_size: int, chunk_overlap: int, strategy: str, db: Session):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc: return

    try:
        if not has_ai_libs:
            raise Exception("AI Libraries not installed")

        # 1. Read File
        text = ""
        if file_path.lower().endswith('.pdf'):
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() or ""
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
                
        # 2. Split Text
        if strategy == "paragraph":
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size, 
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""]
            )
        else:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size, 
                chunk_overlap=chunk_overlap
            )
        chunks = text_splitter.split_text(text)
        
        # 3. Create/Load FAISS
        global embeddings_model
        if embeddings_model is None:
            # use a fast lightweight model
            embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
        index_path = f"vector_store/tenant_{tenant_id}"
        metadatas = [{"document_id": document_id, "source": doc.name} for _ in chunks]

        if os.path.exists(index_path):
            vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
            vectorstore.add_texts(texts=chunks, metadatas=metadatas)
        else:
            vectorstore = FAISS.from_texts(texts=chunks, embedding=embeddings_model, metadatas=metadatas)
            
        vectorstore.save_local(index_path)
        
        # Save chunks to SQLite for relational tracking
        for i, chunk_text in enumerate(chunks):
            db_chunk = models.DocumentChunk(
                document_id=document_id,
                content=chunk_text,
                overlap_chars=chunk_overlap,
                chunk_index=i
            )
            db.add(db_chunk)
        
        # 4. Update status
        doc.status = "Completed"
        doc.embeddings_count = len(chunks)
        db.commit()
        
    except Exception as e:
        print(f"Error processing document: {e}")
        doc.status = "Failed"
        db.commit()

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
    chunking_strategy: str = Form("fixed"), # "fixed" or "paragraph"
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    # Read file to get size
    content = await file.read()
    file_size = len(content)
    
    # Save file to disk temporarily
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(content)
        
    # Create DB entry
    doc = models.Document(
        tenant_id=current_user.tenant_id,
        name=file.filename,
        file_type="PDF" if file.filename.lower().endswith('.pdf') else "TXT",
        size=file_size,
        status="Processing",
        embeddings_count=0
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # Start background processing
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
        
    # Delete from FAISS
    try:
        global embeddings_model
        if embeddings_model is None:
            embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        index_path = f"vector_store/tenant_{current_user.tenant_id}"
        if os.path.exists(index_path):
            vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
            
            # Find document ids in FAISS matching document_id
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

@router.get("/{document_id}/chunks")
def get_document_chunks(
    document_id: int,
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    # Validate user owns document
    doc = db.query(models.Document).filter(
        models.Document.id == document_id, 
        models.Document.tenant_id == current_user.tenant_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    chunks = []
    try:
        global embeddings_model
        if embeddings_model is None:
            embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
        index_path = f"vector_store/tenant_{current_user.tenant_id}"
        if os.path.exists(index_path):
            vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
            docstore_dict = vectorstore.docstore._dict
            
            for uid, doc_data in docstore_dict.items():
                if doc_data.metadata.get("document_id") == document_id:
                    chunks.append({
                        "id": uid,
                        "content": doc_data.page_content,
                        "metadata": doc_data.metadata
                    })
    except Exception as e:
        print(f"Failed to load chunks: {e}")
        raise HTTPException(status_code=500, detail="Failed to load chunks")
        
    return {"chunks": chunks}

@router.post("/search")
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
            embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
        index_path = f"vector_store/tenant_{current_user.tenant_id}"
        if not os.path.exists(index_path):
             return {"results": []}

        vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
        docs = vectorstore.similarity_search_with_score(query.query, k=3)
        
        results = []
        for doc, score in docs:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
            
        return {"results": results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
