import sys
sys.path.append('.')
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
index_path = "vector_store/tenant_1"

if os.path.exists(index_path):
    print("FAISS index exists.")
    try:
        vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
        query = "rag"
        print(f"Searching for query: '{query}'")
        docs = vectorstore.similarity_search_with_score(query, k=3)
        print("Total results found:", len(docs))
        for i, (doc, score) in enumerate(docs):
            print(f"Match #{i+1}: Score={score:.4f}, Source={doc.metadata.get('source')}, Document ID={doc.metadata.get('document_id')}")
            print(f"Content: {doc.page_content[:150]}...")
    except Exception as e:
        print("Error during search:", e)
else:
    print("FAISS index does NOT exist.")
