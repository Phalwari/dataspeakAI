import asyncio
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("dataspeakai.profiling_queue")

MAX_PARALLEL_JOBS = 2       # Max concurrent profiling jobs running simultaneously
MAX_JOB_DURATION_SEC = 180  # 3 minutes timeout per job

class ProfilingQueueManager:
    def __init__(self, max_parallel: int = MAX_PARALLEL_JOBS):
        self._semaphore = asyncio.Semaphore(max_parallel)
        self._llm_semaphore = asyncio.Semaphore(2)
        self._jobs: Dict[int, Dict[str, Any]] = {}
        self._waiting_queue = []
        self._llm_timestamps = []
        self._lock = asyncio.Lock()

    def record_llm_call(self):
        now = time.time()
        self._llm_timestamps.append(now)
        # Purge timestamps older than 60s
        self._llm_timestamps = [t for t in self._llm_timestamps if now - t <= 60]

    def get_llm_calls_last_minute(self) -> int:
        now = time.time()
        self._llm_timestamps = [t for t in self._llm_timestamps if now - t <= 60]
        return len(self._llm_timestamps)

    async def get_job_status(self, connection_id: int) -> Dict[str, Any]:
        async with self._lock:
            if connection_id in self._jobs:
                job = self._jobs[connection_id]
                pos = 0
                if job["status"] == "queued" and connection_id in self._waiting_queue:
                    pos = self._waiting_queue.index(connection_id) + 1
                return {
                    "connection_id": connection_id,
                    "status": job["status"],
                    "queue_position": pos,
                    "elapsed_sec": round(time.time() - job["queued_at"], 1) if "queued_at" in job else 0,
                    "error": job.get("error")
                }
            return {"connection_id": connection_id, "status": "idle", "queue_position": 0}

    async def enqueue_and_run(self, tenant_id: int, connection_id: int, job_fn, *args, **kwargs):
        async with self._lock:
            self._jobs[connection_id] = {
                "tenant_id": tenant_id,
                "status": "queued",
                "queued_at": time.time(),
                "error": None
            }
            if connection_id not in self._waiting_queue:
                self._waiting_queue.append(connection_id)

        try:
            async with self._semaphore:
                async with self._lock:
                    if connection_id in self._waiting_queue:
                        self._waiting_queue.remove(connection_id)
                    self._jobs[connection_id]["status"] = "processing"
                    self._jobs[connection_id]["started_at"] = time.time()

                logger.info(f"[Queue] Starting profiling for connection {connection_id} (Tenant {tenant_id})")
                
                # Execute with strict timeout protection
                await asyncio.wait_for(job_fn(tenant_id, connection_id, *args, **kwargs), timeout=MAX_JOB_DURATION_SEC)

                async with self._lock:
                    self._jobs[connection_id]["status"] = "completed"
                    self._jobs[connection_id]["completed_at"] = time.time()

        except asyncio.TimeoutError:
            logger.error(f"[Queue] Job timed out for connection {connection_id} after {MAX_JOB_DURATION_SEC}s")
            async with self._lock:
                self._jobs[connection_id]["status"] = "failed"
                self._jobs[connection_id]["error"] = f"Profiling timed out after {MAX_JOB_DURATION_SEC}s"
        except Exception as ex:
            logger.error(f"[Queue] Job error for connection {connection_id}: {ex}")
            async with self._lock:
                self._jobs[connection_id]["status"] = "failed"
                self._jobs[connection_id]["error"] = str(ex)

    def get_stats(self) -> Dict[str, Any]:
        queued_count = sum(1 for j in self._jobs.values() if j["status"] == "queued")
        active_count = sum(1 for j in self._jobs.values() if j["status"] == "processing")
        return {
            "queued_jobs": queued_count,
            "active_jobs": active_count,
            "total_tracked_jobs": len(self._jobs),
            "llm_calls_last_minute": self.get_llm_calls_last_minute()
        }

profiling_queue = ProfilingQueueManager(max_parallel=MAX_PARALLEL_JOBS)
