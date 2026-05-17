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
        docstore_dict = vectorstore.docstore._dict
        print("Total items in FAISS docstore:", len(docstore_dict))
        
        all_metadata = []
        for uid, doc_data in docstore_dict.items():
            all_metadata.append(doc_data.metadata)
        
        print("Unique document_ids in metadata:")
        doc_ids = set(m.get("document_id") for m in all_metadata)
        print(doc_ids)
        
        print("Sample metadata items:")
        for m in list(all_metadata)[:5]:
            print(m)

    except Exception as e:
        print("Error reading FAISS:", e)
else:
    print("FAISS index does NOT exist.")
