import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def test_chunking(text, chunk_size, chunk_overlap):
    print(f"\n--- Testing with chunk_size={chunk_size}, chunk_overlap={chunk_overlap} ---")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_text(text)
    print(f"Number of chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks[:3]): # Show first 3 chunks
        print(f"Chunk {i+1} (length {len(chunk)}): {chunk[:100]}...")
    return chunks

def test_rag_retrieval(chunks, query):
    print(f"\n--- Testing Retrieval for query: '{query}' ---")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_texts(chunks, embeddings)
    
    results = vectorstore.similarity_search(query, k=2)
    print(f"Top 2 results:")
    for i, res in enumerate(results):
        print(f"Result {i+1}: {res.page_content[:200]}...")

if __name__ == "__main__":
    sample_text = """
    DataSpeakAI is a revolutionary platform that connects to your databases and documents.
    It uses advanced AI models to provide insights and answer questions in real-time.
    The platform supports various database types including PostgreSQL, MySQL, and MongoDB.
    Users can upload PDF, TXT, and CSV files to build a private knowledge base.
    Security is a top priority, with enterprise-grade encryption and strict data isolation.
    Multi-tenancy is built-in from the ground up, ensuring that each organization's data is isolated.
    The AI assistant can be embedded into any website using a simple script tag.
    It uses RAG (Retrieval-Augmented Generation) to ground its answers in your specific data.
    Chunking and overlapping are key parts of the RAG process.
    Smaller chunks provide more granular retrieval, while larger chunks provide more context.
    Overlapping ensures that context is not lost at the boundaries of chunks.
    """
    
    # Test 1: Standard settings
    chunks1 = test_chunking(sample_text, chunk_size=100, chunk_overlap=20)
    
    # Test 2: Larger chunks, no overlap
    chunks2 = test_chunking(sample_text, chunk_size=300, chunk_overlap=0)
    
    # Test 3: Small chunks, high overlap
    chunks3 = test_chunking(sample_text, chunk_size=50, chunk_overlap=25)
    
    # Test Retrieval
    test_rag_retrieval(chunks1, "What databases are supported?")
    test_rag_retrieval(chunks1, "Is security a priority?")
