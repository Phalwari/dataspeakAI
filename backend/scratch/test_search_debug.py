import sys
sys.path.append('.')
import os
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
index_path = "vector_store/tenant_1"

if os.path.exists(index_path):
    print("FAISS index exists.")
    try:
        vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
        query = "rag"
        print(f"Searching for query: '{query}' with k=40 deep search")
        
        embedding = embeddings_model.embed_query(query)
        scores, indices = vectorstore.index.search(np.array([embedding], dtype=np.float32), 40)
        
        docs = []
        for score, i in zip(scores[0], indices[0]):
            if i == -1:
                continue
            try:
                _id = vectorstore.index_to_docstore_id[int(i)]
                doc = vectorstore.docstore.search(_id)
                docs.append((doc, score))
            except KeyError:
                continue
                
        print("Total valid results found:", len(docs))
        for i, (doc, score) in enumerate(docs):
            print(f"Rank #{i+1}: Score={score:.4f}, Source={doc.metadata.get('source')}, Document ID={doc.metadata.get('document_id')}")
            print(f"Content: {doc.page_content[:120]}...")
            
    except Exception as e:
         print("ERROR:", e)
else:
    print("FAISS index does NOT exist.")
