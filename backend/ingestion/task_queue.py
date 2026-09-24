import logging
from celery_app import celery_app
from database import SessionLocal

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_document_task(self, document_id: int, file_path: str, tenant_id: int, chunk_size: int, chunk_overlap: int, strategy: str):
    """
    Celery background task wrapper for processing document uploads.
    """
    db = SessionLocal()
    try:
        from routers.documents import process_document
        process_document(document_id, file_path, tenant_id, chunk_size, chunk_overlap, strategy, db)
    except Exception as exc:
        logger.error(f"Error processing document {document_id} in Celery task: {exc}")
        try:
            self.retry(exc=exc)
        except Exception:
            raise exc
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def reindex_document_task(self, document_id: int, tenant_id: int):
    """
    Celery background task wrapper for re-embedding stored document chunks.
    """
    db = SessionLocal()
    try:
        from routers.documents import reembed_stored_chunks
        reembed_stored_chunks(document_id, tenant_id, db)
    except Exception as exc:
        logger.error(f"Error reindexing document {document_id} in Celery task: {exc}")
        try:
            self.retry(exc=exc)
        except Exception:
            raise exc
    finally:
        db.close()
