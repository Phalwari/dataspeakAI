import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure backend directory is in sys.path so 'import models', 'import schemas' work consistently
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
import schemas
from routers.documents import search_documents, process_document
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestRAGSynthesis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an in-memory SQLite DB for testing ORM models
        cls.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        
    def setUp(self):
        self.db = self.SessionLocal()
        # Mock current user with tenant_id = 999
        self.mock_user = MagicMock(spec=models.User)
        self.mock_user.id = 1
        self.mock_user.tenant_id = 999
        self.tenant_id = 999
        self.vector_dir = f"vector_store/tenant_{self.tenant_id}"
        
        # Clean up vector store if exists
        if os.path.exists(self.vector_dir):
            shutil.rmtree(self.vector_dir)

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.vector_dir):
            shutil.rmtree(self.vector_dir)

    def test_no_index_path(self):
        """Test search when no FAISS index exists for tenant."""
        q = schemas.SearchQuery(query="What is DataSpeakAI?")
        res = search_documents(query=q, current_user=self.mock_user, db=self.db)
        self.assertEqual(res["query"], "What is DataSpeakAI?")
        self.assertIn("No indexed documents found", res["answer"])
        self.assertEqual(res["results"], [])

    def test_fallback_when_gemini_key_absent(self):
        """Test search synthesis fallback when GEMINI_API_KEY is absent."""
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
        
        emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        texts = [
            "DataSpeakAI is a Conversational AI platform for enterprise databases.",
            "It connects PostgreSQL, MySQL, and SQLite databases to natural language.",
            "RAG module allows querying PDF documents using FAISS and embeddings."
        ]
        metadatas = [
            {"document_id": 1, "source": "overview.pdf"},
            {"document_id": 1, "source": "overview.pdf"},
            {"document_id": 2, "source": "rag_docs.pdf"}
        ]
        vectorstore = FAISS.from_texts(texts=texts, embedding=emb, metadatas=metadatas)
        os.makedirs(self.vector_dir, exist_ok=True)
        vectorstore.save_local(self.vector_dir)

        # Ensure GEMINI_API_KEY is removed
        env_copy = os.environ.copy()
        if "GEMINI_API_KEY" in env_copy:
            del env_copy["GEMINI_API_KEY"]
        
        with patch.dict(os.environ, env_copy, clear=True):
            q = schemas.SearchQuery(query="What database systems does DataSpeakAI support?", top_k=2, synthesize=True)
            res = search_documents(query=q, current_user=self.mock_user, db=self.db)
            
            self.assertEqual(res["query"], q.query)
            self.assertEqual(len(res["results"]), 2)
            self.assertIsNotNone(res["answer"])
            self.assertIn("Synthesized summary from", res["answer"])
            self.assertIn("[Source:", res["answer"])
            print("\n[TEST OUTPUT - Fallback Answer]:\n", res["answer"])

    def test_synthesis_with_gemini_key(self):
        """Test search synthesis with Gemini API call (mocked response)."""
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
        
        emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        texts = [
            "DataSpeakAI uses Fernet encryption for storing database passwords at rest securely."
        ]
        metadatas = [{"document_id": 3, "source": "security_policy.txt"}]
        vectorstore = FAISS.from_texts(texts=texts, embedding=emb, metadatas=metadatas)
        os.makedirs(self.vector_dir, exist_ok=True)
        vectorstore.save_local(self.vector_dir)

        # Mock requests.post for Gemini API call
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key"}):
            with patch("requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "candidates": [{
                        "content": {
                            "parts": [{
                                "text": "DataSpeakAI uses Fernet symmetric encryption to secure database passwords at rest [Source: security_policy.txt]."
                            }]
                        }
                    }]
                }
                mock_post.return_value = mock_response

                q = schemas.SearchQuery(query="How are passwords encrypted?", top_k=3, synthesize=True)
                res = search_documents(query=q, current_user=self.mock_user, db=self.db)

                self.assertEqual(res["query"], q.query)
                self.assertEqual(len(res["results"]), 1)
                self.assertIn("Fernet symmetric encryption", res["answer"])
                self.assertIn("[Source: security_policy.txt]", res["answer"])
                print("\n[TEST OUTPUT - Gemini Answer]:\n", res["answer"])

    def test_synthesize_false(self):
        """Test search when synthesize parameter is set to False."""
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
        
        emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        texts = ["Test document content for RAG search."]
        vectorstore = FAISS.from_texts(texts=texts, embedding=emb, metadatas=[{"document_id": 4, "source": "test.txt"}])
        os.makedirs(self.vector_dir, exist_ok=True)
        vectorstore.save_local(self.vector_dir)

        q = schemas.SearchQuery(query="Test document", synthesize=False)
        res = search_documents(query=q, current_user=self.mock_user, db=self.db)

        self.assertIsNone(res["answer"])
        self.assertEqual(len(res["results"]), 1)

    def test_gemini_api_failure_fallback(self):
        """Test fallback synthesis when Gemini API returns 500 or raises exception."""
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
        
        emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        texts = ["Critical system security configuration details."]
        vectorstore = FAISS.from_texts(texts=texts, embedding=emb, metadatas=[{"document_id": 5, "source": "config.txt"}])
        os.makedirs(self.vector_dir, exist_ok=True)
        vectorstore.save_local(self.vector_dir)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key"}):
            with patch("requests.post", side_effect=Exception("Network error")):
                q = schemas.SearchQuery(query="security configuration", synthesize=True)
                res = search_documents(query=q, current_user=self.mock_user, db=self.db)
                self.assertIsNotNone(res["answer"])
                self.assertIn("Synthesized summary from", res["answer"])

if __name__ == "__main__":
    unittest.main()
