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

def process_document(document_id: int, file_path: str, tenant_id: int, chunk_size: int, chunk_overlap: int, strategy: str, db: Session):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc: return

    try:
        if not has_ai_libs:
            raise Exception("AI Libraries not installed")

        # 1. Read File
        text = ""
        line_count = 0
        paragraph_count = 0
        table_count = 0
        image_count = 0
        
        standalone_chunks = []
        
        if file_path.lower().endswith('.pdf'):
            import pdfplumber
            # Extract regular page text and identify tables/images counts
            with pdfplumber.open(file_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
                    
                    try:
                        tables = page.extract_tables()
                        if tables:
                            table_count += len(tables)
                            for tbl in tables:
                                md_table = table_to_markdown(tbl)
                                if md_table:
                                    standalone_chunks.append(md_table)
                    except Exception as tbl_err:
                        print(f"Failed to extract structured table on page {page_idx+1}: {tbl_err}")
                        
                    if page.images:
                        image_count += len(page.images)
            
            # Image Extraction & Visual Processing (Exclusively Google Gemini 1.5 Flash API)
            try:
                import fitz  # PyMuPDF
                import base64
                import requests
                
                doc_pdf = fitz.open(file_path)
                gemini_api_key = os.getenv("GEMINI_API_KEY")
                
                if not gemini_api_key:
                    print("Google Gemini API Key is missing in .env. Bypassing image visual extraction.")
                else:
                    for page_num in range(len(doc_pdf)):
                        page = doc_pdf[page_num]
                        image_list = page.get_images(full=True)
                        for img_idx, img in enumerate(image_list):
                            xref = img[0]
                            base_image = doc_pdf.extract_image(xref)
                            image_bytes = base_image["image"]
                            
                            visual_description = ""
                            try:
                                image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
                                payload = {
                                    "contents": [{
                                        "parts": [
                                            {"text": "Analyze this chart, diagram, or image from a technical document. Perform high-precision OCR on any text, figures, and numbers, and generate a detailed visual analysis of the trends and key takeaways for a RAG knowledge base query assistant."},
                                            {
                                                "inlineData": {
                                                    "mimeType": "image/png",
                                                    "data": image_b64
                                                }
                                            }
                                        ]
                                    }]
                                }
                                headers = {"Content-Type": "application/json"}
                                res = requests.post(gemini_url, json=payload, headers=headers, timeout=30)
                                if res.status_code == 200:
                                    res_data = res.json()
                                    visual_description = res_data["candidates"][0]["content"]["parts"][0]["text"]
                            except Exception as gemini_err:
                                print(f"Google Gemini API vision call failed on page {page_num+1} img {img_idx}: {gemini_err}")
                            
                            if visual_description:
                                img_chunk = f"[Visual Content from page {page_num+1} of {doc.name} (Parsed via Google Gemini 2.5 Flash)]\n"
                                img_chunk += visual_description
                                standalone_chunks.append(img_chunk)
            except Exception as img_err:
                print(f"PyMuPDF image extraction failed or was bypassed: {img_err}")
                
            import re
            sentences = re.split(r'[.!?]+', text)
            sentence_count = len([s for s in sentences if s.strip()])
            paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
                
            import re
            sentences = re.split(r'[.!?]+', text)
            sentence_count = len([s for s in sentences if s.strip()])
            paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
                
        # 2. Split Text
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        if strategy == "paragraph":
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size, 
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""]
            )
        elif strategy == "line":
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size, 
                chunk_overlap=chunk_overlap,
                separators=["\n", ". ", "? ", "! ", " ", ""]
            )
        elif strategy == "sentence":
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size, 
                chunk_overlap=chunk_overlap,
                separators=[". ", "? ", "! ", " ", ""]
            )
        else:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size, 
                chunk_overlap=chunk_overlap
            )
            
        chunks = text_splitter.split_text(text)
        
        # Merge standard chunks with our standalone Markdown table & Image OCR/Vision chunks!
        chunks.extend(standalone_chunks)
        
        # 3. Create/Load FAISS
        global embeddings_model
        if embeddings_model is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
        index_path = f"vector_store/tenant_{tenant_id}"
        metadatas = [{"document_id": document_id, "source": doc.name} for _ in chunks]

        from langchain_community.vectorstores import FAISS
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
        doc.line_count = sentence_count
        doc.paragraph_count = paragraph_count
        doc.table_count = table_count
        doc.image_count = image_count
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
            from langchain_huggingface import HuggingFaceEmbeddings
            embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        index_path = f"vector_store/tenant_{current_user.tenant_id}"
        if os.path.exists(index_path):
            from langchain_community.vectorstores import FAISS
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
        db_chunks = db.query(models.DocumentChunk).filter(
            models.DocumentChunk.document_id == document_id
        ).order_by(models.DocumentChunk.chunk_index).all()
        
        for chunk in db_chunks:
            chunks.append({
                "id": str(chunk.id),
                "content": chunk.content,
                "metadata": {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "overlap_chars": chunk.overlap_chars
                }
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
            from langchain_huggingface import HuggingFaceEmbeddings
            embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
        index_path = f"vector_store/tenant_{current_user.tenant_id}"
        if not os.path.exists(index_path):
             return {"results": []}

        import numpy as np
        from langchain_community.vectorstores import FAISS
        vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
        
        # Safe custom similarity search to prevent numpy/compatibility KeyErrors and skip stale orphan indices
        embedding = embeddings_model.embed_query(query.query)
        # Deep search (k=100) to collect all candidates, guaranteeing stale indexes never crowd out valid docs
        scores, indices = vectorstore.index.search(np.array([embedding], dtype=np.float32), 100)
        
        results = []
        for score, i in zip(scores[0], indices[0]):
            if i == -1:
                continue
            try:
                # Cast index to standard python int to avoid numpy 2.x np.int64 KeyError
                _id = vectorstore.index_to_docstore_id[int(i)]
                doc = vectorstore.docstore.search(_id)
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
            except KeyError:
                # Skip stale/orphan indices that don't exist in the current docstore
                continue
            
        # Return top 5 valid matches to ensure a diverse set of source document results are visible in the UI
        return {"results": results[:5]}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
