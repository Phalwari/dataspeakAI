import logging
from celery_app import celery_app
from database import SessionLocal

logger = logging.getLogger(__name__)


def _retry_transient(task, exc, db, document_id):
    """Retry transport/lock failures; malformed documents need user correction."""
    from sqlalchemy.exc import OperationalError
    import httpx
    import requests
    import models
    transient = isinstance(exc, (TimeoutError, ConnectionError, OperationalError,
                                 httpx.TransportError, requests.ConnectionError,
                                 requests.Timeout))
    if transient and task.request.retries < task.max_retries:
        db.rollback()
        doc = db.get(models.Document, document_id)
        if doc and not doc.is_deleted:
            doc.progress_step = "retrying"
            db.commit()
            raise task.retry(exc=exc, countdown=30 * (2 ** task.request.retries))
    raise exc

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
        logger.error("Document %s ingestion failed (%s)", document_id, type(exc).__name__)
        _retry_transient(self, exc, db, document_id)
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
        logger.error("Document %s reindex failed (%s)", document_id, type(exc).__name__)
        _retry_transient(self, exc, db, document_id)
    finally:
        db.close()
