"""
Reconciliation script for SQL/index drift, orphan artifacts, interrupted jobs, and stale generation pointers.
Task NR-2.2-B-T09.
Supports:
  --dry-run: Inspects and outputs drift report without modifying state
  --fix: Applies repairs to stalled jobs and prunes orphaned files
"""
import os
import sys
import argparse
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime, timedelta

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from typing import Optional
from sqlalchemy.orm import Session
from database import SessionLocal
import models

def to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        import datetime as dt_module
        return dt.astimezone(dt_module.timezone.utc).replace(tzinfo=None)
    return dt


def _source_snapshot(db, tenant_id, model_name):
    """Read authoritative source rows; refuse to race an in-flight publication."""
    db.expire_all()
    docs = db.query(models.Document).filter(models.Document.tenant_id == tenant_id).all()
    docs = [d for d in docs if (d.embedding_model or "all-MiniLM-L6-v2") == model_name and not d.is_deleted]
    if any(d.status == "Processing" for d in docs):
        raise RuntimeError("Ingestion is active; retry reconciliation after jobs finish")
    texts, metadata = [], []
    for doc in docs:
        if doc.status != "Completed":
            continue
        chunks = db.query(models.DocumentChunk).filter_by(document_id=doc.id).order_by(models.DocumentChunk.chunk_index).all()
        children = [c for c in chunks if c.parent_chunk_id is not None]
        for chunk in children or chunks:
            texts.append(chunk.content)
            metadata.append({"chunk_id": chunk.id, "document_id": doc.id, "source": doc.name,
                             "version": doc.version, "parent_chunk_id": chunk.parent_chunk_id,
                             "hierarchy_level": chunk.hierarchy_level, "page_number": chunk.page_number,
                             "content_type": chunk.content_type, "reference_id": chunk.reference_id,
                             "section_heading": chunk.section_heading})
    return texts, metadata


def _reconcile_generation(db, tenant_id, model_name, dry_run):
    from search.generation_manager import IndexGenerationManager
    manager = IndexGenerationManager(tenant_id, model_name)
    result = {"tenant_id": tenant_id, "model_name": model_name, "issues": [], "repaired": False}
    try:
        texts, metadata = _source_snapshot(db, tenant_id, model_name)
    except RuntimeError as exc:
        result["deferred"] = str(exc)
        return result
    expected = {(m["chunk_id"], m["document_id"], m["version"], hashlib.sha256(t.encode("utf-8")).hexdigest())
                for t, m in zip(texts, metadata)}
    try:
        pointer = json.loads(Path(manager.pointer_file).read_text(encoding="utf-8"))
        name = pointer["active_generation"]
        if not isinstance(name, str) or not re.fullmatch(r"gen_\d+_[a-f0-9]+", name):
            raise ValueError("Invalid generation name")
        active = Path(manager.tenant_dir) / name
        if not all((active / filename).is_file() for filename in ("index.faiss", "index.pkl", "bm25.pkl", "manifest.json")):
            raise ValueError("Incomplete generation")
        manifest = json.loads((active / "manifest.json").read_text(encoding="utf-8"))
        actual = {(m["chunk_id"], m["document_id"], m["version"], m["sha256"]) for m in manifest}
        if actual != expected or len(manifest) != len(expected) or pointer.get("chunk_count") != len(expected):
            result["issues"].append("sql_index_drift")
    except (OSError, ValueError, KeyError, TypeError):
        result["issues"].append("missing_or_invalid_generation")
    if result["issues"] and not dry_run:
        try:
            from routers.documents import _document_embeddings
            manager.build_and_publish_generation(_document_embeddings(model_name), [], [], [],
                source_snapshot=lambda: _source_snapshot(db, tenant_id, model_name),
                live_document_ids=lambda: {row.id for row in db.query(models.Document.id).filter(
                    models.Document.tenant_id == tenant_id, models.Document.is_deleted == False).all()})
            result["repaired"] = True
        except Exception as exc:
            result["repair_error"] = str(exc)
    return result

def reconcile_indexes(dry_run: bool = True, db: Optional[Session] = None):
    print(f"=== Starting Index & Ingestion Reconciliation (Mode: {'DRY-RUN' if dry_run else 'FIX'}) ===")
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    stalled_docs = []
    orphan_files = []
    staging_pruned = 0
    generation_reports = []
    orphan_index_dirs = []
    
    try:
        now = datetime.utcnow()
        stalled_threshold = now - timedelta(minutes=10)

        # 1. Detect documents stuck in Processing with heartbeat > 10m
        processing_docs = db.query(models.Document).filter(
            models.Document.status == "Processing"
        ).all()

        for d in processing_docs:
            heartbeat = to_naive_utc(d.last_heartbeat_at or d.created_at)
            if heartbeat and heartbeat < stalled_threshold:
                stalled_docs.append(d)
                print(f"[STALLED JOB] Doc ID: {d.id}, Name: {d.name}, Step: {d.progress_step}, Last Heartbeat: {heartbeat}")
                if not dry_run:
                    d.status = "Failed"
                    d.progress_step = "failed"
                    d.error_message = "Ingestion stalled: heartbeat expired (>10 minutes without progress)"
                    d.last_heartbeat_at = now

        if not dry_run and stalled_docs:
            db.commit()
            print(f"-> Marked {len(stalled_docs)} stalled documents as Failed.")

        # 2. Check for orphaned ephemeral files in uploads/
        if os.path.exists("uploads"):
            for fname in os.listdir("uploads"):
                fpath = os.path.join("uploads", fname)
                if os.path.isfile(fpath):
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    if mtime < now - timedelta(hours=1):
                        orphan_files.append(fpath)
                        print(f"[ORPHAN UPLOAD] File: {fpath}, Modified: {mtime}")
                        if not dry_run:
                            try:
                                os.remove(fpath)
                            except Exception as err:
                                print(f"Failed removing {fpath}: {err}")

        if not dry_run and orphan_files:
            print(f"-> Pruned {len(orphan_files)} orphaned upload files.")

        # 3. Compare current SQL chunks with the readable generation manifests.
        groups = {(d.tenant_id, d.embedding_model or "all-MiniLM-L6-v2")
                  for d in db.query(models.Document).all()}
        for tenant_id, model_name in sorted(groups):
            generation_reports.append(_reconcile_generation(db, tenant_id, model_name, dry_run))

        # 4. Check stale staging directories without racing an active publisher.
        if os.path.exists("vector_store"):
            from search.generation_manager import IndexGenerationManager, ProcessTenantLock
            known_dirs = {Path(IndexGenerationManager(t, m).tenant_dir).resolve() for t, m in groups}
            root = Path("vector_store").resolve()
            for t_dir in os.listdir("vector_store"):
                tenant_path = (root / t_dir).resolve()
                if not tenant_path.is_relative_to(root) or not tenant_path.is_dir():
                    continue
                if (tenant_path / "active_generation.json").exists() and tenant_path not in known_dirs:
                    orphan_index_dirs.append(str(tenant_path))
                staging_dir = os.path.join("vector_store", t_dir, ".staging")
                if os.path.exists(staging_dir) and os.path.isdir(staging_dir):
                    for s_item in os.listdir(staging_dir):
                        s_path = os.path.join(staging_dir, s_item)
                        mtime = datetime.fromtimestamp(os.path.getmtime(s_path))
                        if mtime < now - timedelta(minutes=30):
                            print(f"[STALE STAGING] {s_path}, Modified: {mtime}")
                            staging_pruned += 1
                            if not dry_run:
                                import shutil
                                resolved = Path(s_path).resolve()
                                if resolved.is_relative_to(root) and resolved.is_dir():
                                    try:
                                        with ProcessTenantLock(str(tenant_path / ".generation.lock"), timeout=0.05):
                                            shutil.rmtree(resolved)
                                    except (TimeoutError, OSError):
                                        pass

        print("\n=== Reconciliation Summary ===")
        print(f"Stalled Processing Jobs: {len(stalled_docs)}")
        print(f"Orphan Upload Files: {len(orphan_files)}")
        print(f"Stale Staging Directories: {staging_pruned}")
        print("Reconciliation complete.\n")

        return {
            "stalled_jobs_count": len(stalled_docs),
            "orphan_files_count": len(orphan_files),
            "stale_staging_count": staging_pruned,
            "generation_reports": generation_reports,
            "orphan_index_directories": orphan_index_dirs,
            "retention_note": "Published and orphan generations are retained until readers and rollback retention are resolved."
        }

    finally:
        if close_db:
            db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcile SQL, indexes, and ingestion jobs.")
    parser.add_argument("--fix", action="store_true", help="Apply fixes (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run without applying fixes")
    args = parser.parse_args()

    is_dry_run = not args.fix
    reconcile_indexes(dry_run=is_dry_run)
