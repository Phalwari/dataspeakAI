import sys
sys.path.append('.')
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
index_path = "vector_store/tenant_1"

if os.path.exists(index_path):
    try:
        vectorstore = FAISS.load_local(index_path, embeddings_model, allow_dangerous_deserialization=True)
        print("index_to_docstore_id keys type:", type(list(vectorstore.index_to_docstore_id.keys())[0]))
        print("Sample keys of index_to_docstore_id:")
        print(list(vectorstore.index_to_docstore_id.keys())[:15])
        print("Total keys in index_to_docstore_id:", len(vectorstore.index_to_docstore_id))
    except Exception as e:
        print("ERROR:", e)
