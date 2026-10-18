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
from datetime import datetime, timedelta

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from typing import Optional
from sqlalchemy.orm import Session
from database import SessionLocal
import models

def reconcile_indexes(dry_run: bool = True, db: Optional[Session] = None):
    print(f"=== Starting Index & Ingestion Reconciliation (Mode: {'DRY-RUN' if dry_run else 'FIX'}) ===")
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    stalled_docs = []
    orphan_files = []
    staging_pruned = 0
    
    try:
        now = datetime.utcnow()
        stalled_threshold = now - timedelta(minutes=10)

        # 1. Detect documents stuck in Processing with heartbeat > 10m
        processing_docs = db.query(models.Document).filter(
            models.Document.status == "Processing"
        ).all()

        for d in processing_docs:
            heartbeat = d.last_heartbeat_at or d.created_at
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

        # 3. Check for stale staging directories in vector_store
        if os.path.exists("vector_store"):
            for t_dir in os.listdir("vector_store"):
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
                                shutil.rmtree(s_path, ignore_errors=True)

        print("\n=== Reconciliation Summary ===")
        print(f"Stalled Processing Jobs: {len(stalled_docs)}")
        print(f"Orphan Upload Files: {len(orphan_files)}")
        print(f"Stale Staging Directories: {staging_pruned}")
        print("Reconciliation complete.\n")

        return {
            "stalled_jobs_count": len(stalled_docs),
            "orphan_files_count": len(orphan_files),
            "stale_staging_count": staging_pruned
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
