"""
FormAI Queue Manager

Redis-based job queue for distributing automation jobs to workers.
"""

import redis
from urllib.parse import urlparse
from typing import Optional, List, Dict, Any
from job_models import Job, JobResult, JobStats, WorkerStatus
import json
import os
import time
import socket
from datetime import datetime


class QueueManager:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        parsed = urlparse(redis_url)
        self.redis = redis.Redis(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            db=0,
            decode_responses=True,
            health_check_interval=30
        )
        # Job queues
        self.pending_key = "formai:jobs:pending"
        self.processing_key = "formai:jobs:processing"
        self.completed_key = "formai:jobs:completed"
        self.failed_key = "formai:jobs:failed"
        # Job details (hash)
        self.job_details_prefix = "formai:job:"
        # Worker tracking
        self.workers_key = "formai:workers"

    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        try:
            self.redis.ping()
            return True
        except:
            return False

    # ==================== Job Management ====================

    def add_job(self, job: Job) -> str:
        """Add job to pending queue and store details."""
        job_data = job.model_dump_json()
        # Store job details in hash for quick lookup
        self.redis.hset(f"{self.job_details_prefix}{job.job_id}", mapping={
            "data": job_data,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        })
        # Add to pending queue
        self.redis.lpush(self.pending_key, job.job_id)
        return job.job_id

    def get_job(self, timeout: int = 5) -> Optional[Job]:
        """Pop job from pending queue (blocking)."""
        result = self.redis.brpop(self.pending_key, timeout=timeout)
        if result:
            job_id = result[1]
            job_data = self.redis.hget(f"{self.job_details_prefix}{job_id}", "data")
            if job_data:
                return Job.model_validate_json(job_data)
        return None

    def start_processing(self, job: Job, worker_id: str):
        """Mark job as processing."""
        self.redis.hset(f"{self.job_details_prefix}{job.job_id}", mapping={
            "status": "processing",
            "worker_id": worker_id,
            "started_at": datetime.utcnow().isoformat()
        })
        self.redis.sadd(self.processing_key, job.job_id)

    def complete_job(self, result: JobResult):
        """Mark job as completed."""
        self.redis.srem(self.processing_key, result.job_id)
        self.redis.hset(f"{self.job_details_prefix}{result.job_id}", mapping={
            "status": "completed",
            "result": result.model_dump_json(),
            "completed_at": datetime.utcnow().isoformat()
        })
        self.redis.lpush(self.completed_key, result.job_id)
        # Keep only last 1000 completed jobs
        self.redis.ltrim(self.completed_key, 0, 999)

    def fail_job(self, result: JobResult):
        """Mark job as failed."""
        self.redis.srem(self.processing_key, result.job_id)
        self.redis.hset(f"{self.job_details_prefix}{result.job_id}", mapping={
            "status": "failed",
            "result": result.model_dump_json(),
            "error": result.error or "Unknown error",
            "completed_at": datetime.utcnow().isoformat()
        })
        self.redis.lpush(self.failed_key, result.job_id)

    def get_job_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get full details for a job."""
        data = self.redis.hgetall(f"{self.job_details_prefix}{job_id}")
        if data:
            return data
        return None

    def get_stats(self) -> JobStats:
        """Get queue statistics."""
        # Count active workers (heartbeat within last 30 seconds)
        workers = self.redis.hgetall(self.workers_key)
        now = time.time()
        active = 0
        idle = 0
        for worker_id, data in workers.items():
            try:
                worker_data = json.loads(data)
                last_heartbeat = worker_data.get("last_heartbeat", 0)
                if now - last_heartbeat < 30:
                    if worker_data.get("status") == "busy":
                        active += 1
                    else:
                        idle += 1
            except:
                pass

        return JobStats(
            pending=int(self.redis.llen(self.pending_key)),
            processing=int(self.redis.scard(self.processing_key)),
            completed=int(self.redis.llen(self.completed_key)),
            failed=int(self.redis.llen(self.failed_key)),
            workers_active=active,
            workers_idle=idle
        )

    def get_recent_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent jobs (completed + failed)."""
        jobs = []
        # Get completed
        completed_ids = self.redis.lrange(self.completed_key, 0, limit // 2)
        for job_id in completed_ids:
            details = self.get_job_details(job_id)
            if details:
                jobs.append({"job_id": job_id, **details})
        # Get failed
        failed_ids = self.redis.lrange(self.failed_key, 0, limit // 2)
        for job_id in failed_ids:
            details = self.get_job_details(job_id)
            if details:
                jobs.append({"job_id": job_id, **details})
        return jobs

    # ==================== Worker Management ====================

    def register_worker(self, worker_id: str, hostname: str = None):
        """Register a worker."""
        if not hostname:
            hostname = socket.gethostname()
        worker_data = {
            "worker_id": worker_id,
            "hostname": hostname,
            "status": "idle",
            "last_heartbeat": time.time(),
            "jobs_completed": 0,
            "jobs_failed": 0,
            "registered_at": datetime.utcnow().isoformat()
        }
        self.redis.hset(self.workers_key, worker_id, json.dumps(worker_data))

    def update_worker_status(self, worker_id: str, status: str, current_job_id: str = None):
        """Update worker status and heartbeat."""
        existing = self.redis.hget(self.workers_key, worker_id)
        if existing:
            worker_data = json.loads(existing)
        else:
            worker_data = {"worker_id": worker_id}

        worker_data["status"] = status
        worker_data["current_job_id"] = current_job_id
        worker_data["last_heartbeat"] = time.time()
        self.redis.hset(self.workers_key, worker_id, json.dumps(worker_data))

    def increment_worker_stats(self, worker_id: str, completed: bool = True):
        """Increment worker job counters."""
        existing = self.redis.hget(self.workers_key, worker_id)
        if existing:
            worker_data = json.loads(existing)
            if completed:
                worker_data["jobs_completed"] = worker_data.get("jobs_completed", 0) + 1
            else:
                worker_data["jobs_failed"] = worker_data.get("jobs_failed", 0) + 1
            self.redis.hset(self.workers_key, worker_id, json.dumps(worker_data))

    def get_workers(self) -> List[Dict[str, Any]]:
        """Get all registered workers."""
        workers = []
        worker_data = self.redis.hgetall(self.workers_key)
        now = time.time()
        for worker_id, data in worker_data.items():
            try:
                parsed = json.loads(data)
                # Check if worker is stale (no heartbeat for 60 seconds)
                last_heartbeat = parsed.get("last_heartbeat", 0)
                if now - last_heartbeat > 60:
                    parsed["status"] = "offline"
                workers.append(parsed)
            except:
                pass
        return workers

    def remove_stale_workers(self, max_age_seconds: int = 300):
        """Remove workers that haven't sent heartbeat."""
        worker_data = self.redis.hgetall(self.workers_key)
        now = time.time()
        for worker_id, data in worker_data.items():
            try:
                parsed = json.loads(data)
                last_heartbeat = parsed.get("last_heartbeat", 0)
                if now - last_heartbeat > max_age_seconds:
                    self.redis.hdel(self.workers_key, worker_id)
            except:
                pass


# Global instance (lazy initialization to avoid connection errors at import)
_queue_manager = None

def get_queue_manager() -> QueueManager:
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = QueueManager()
    return _queue_manager
