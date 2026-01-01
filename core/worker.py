#!/usr/bin/env python3
"""
FormAI Worker - Headless job processor for Docker scaling

Pulls jobs from Redis queue, executes recordings with profile data, reports results.
Designed to run in Docker containers with volume-mounted profiles/recordings.
"""

import asyncio
import os
import sys
import json
import time
import uuid
import signal
import socket
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("formai-worker")

# Imports
from core.queue_manager import get_queue_manager
from core.job_models import Job, JobResult


class FormAIWorker:
    """Headless worker that processes jobs from Redis queue."""

    def __init__(self):
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self.hostname = socket.gethostname()
        self.queue = get_queue_manager()
        self.running = True
        self.current_job: Optional[Job] = None
        self.jobs_completed = 0
        self.jobs_failed = 0

        # Paths (will be volume-mounted in Docker)
        self.profiles_dir = Path(os.getenv("PROFILES_DIR", "/app/profiles"))
        self.recordings_dir = Path(os.getenv("RECORDINGS_DIR", "/app/recordings"))
        self.downloads_dir = Path(os.getenv("DOWNLOADS_DIR", "/app/downloads"))

        # Create downloads dir if needed
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info(f"Worker {self.worker_id} initialized on {self.hostname}")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Worker {self.worker_id} received shutdown signal")
        self.running = False

    def load_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Load profile from disk."""
        profile_path = self.profiles_dir / f"{profile_id}.json"
        if not profile_path.exists():
            # Try without .json extension (if profile_id already includes it)
            profile_path = self.profiles_dir / profile_id
        if not profile_path.exists():
            # Try finding by ID in all profiles
            for f in self.profiles_dir.glob("*.json"):
                try:
                    with open(f, 'r', encoding='utf-8') as fp:
                        profile = json.load(fp)
                        if profile.get("id") == profile_id:
                            return profile
                except:
                    pass
            return None

        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load profile {profile_id}: {e}")
            return None

    def load_recording(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """Load recording from disk."""
        recording_path = self.recordings_dir / f"{recording_id}.json"
        if not recording_path.exists():
            recording_path = self.recordings_dir / recording_id
        if not recording_path.exists():
            # Try finding by ID
            for f in self.recordings_dir.glob("*.json"):
                try:
                    with open(f, 'r', encoding='utf-8') as fp:
                        recording = json.load(fp)
                        if recording.get("id") == recording_id:
                            return recording
                except:
                    pass
            return None

        try:
            with open(recording_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load recording {recording_id}: {e}")
            return None

    async def process_job(self, job: Job) -> JobResult:
        """Process a single automation job using bulk autofill."""
        start_time = time.time()
        result = JobResult(job_id=job.job_id, status="processing")

        try:
            # Load recording and profile
            recording = self.load_recording(job.recording_id)
            if not recording:
                raise Exception(f"Recording '{job.recording_id}' not found")

            profile = self.load_profile(job.profile_id)
            if not profile:
                raise Exception(f"Profile '{job.profile_id}' not found")

            logger.info(f"Executing job {job.job_id}: recording={job.recording_id}, profile={job.profile_id}")

            # Use new AutofillEngine (bulk fill + actions)
            from tools.autofill_engine import AutofillEngine

            engine = AutofillEngine(headless=True)

            # Execute with bulk fill approach
            autofill_result = await engine.execute(
                recording=recording,
                profile=profile
            )

            # Build result (no screenshot needed)
            if autofill_result.success:
                result.status = "success"
                result.fields_filled = autofill_result.fields_filled
                result.form_submitted = autofill_result.submitted
            else:
                result.status = "failed"
                result.error = autofill_result.error

            result.duration_ms = int((time.time() - start_time) * 1000)

            logger.info(f"Job {job.job_id} completed: status={result.status}, "
                       f"fields={autofill_result.fields_filled}, submitted={autofill_result.submitted}, "
                       f"duration={result.duration_ms}ms")

        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {e}", exc_info=True)
            result.status = "failed"
            result.error = str(e)
            result.duration_ms = int((time.time() - start_time) * 1000)

        return result

    async def heartbeat_loop(self):
        """Send periodic heartbeats to Redis."""
        while self.running:
            try:
                status = "busy" if self.current_job else "idle"
                job_id = self.current_job.job_id if self.current_job else None
                self.queue.update_worker_status(self.worker_id, status, job_id)
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
            await asyncio.sleep(10)

    async def run(self):
        """Main worker loop."""
        logger.info(f"Worker {self.worker_id} starting...")

        # Register with Redis
        self.queue.register_worker(self.worker_id, self.hostname)

        # Start heartbeat task
        heartbeat_task = asyncio.create_task(self.heartbeat_loop())

        try:
            while self.running:
                try:
                    # Try to get a job (blocks for 5 seconds)
                    job = self.queue.get_job(timeout=5)

                    if job:
                        self.current_job = job
                        self.queue.start_processing(job, self.worker_id)
                        self.queue.update_worker_status(self.worker_id, "busy", job.job_id)

                        # Process the job
                        result = await self.process_job(job)

                        # Report result
                        if result.status == "success":
                            self.queue.complete_job(result)
                            self.queue.increment_worker_stats(self.worker_id, completed=True)
                            self.jobs_completed += 1
                        else:
                            self.queue.fail_job(result)
                            self.queue.increment_worker_stats(self.worker_id, completed=False)
                            self.jobs_failed += 1

                        self.current_job = None
                        self.queue.update_worker_status(self.worker_id, "idle")

                except Exception as e:
                    logger.error(f"Error in worker loop: {e}", exc_info=True)
                    await asyncio.sleep(5)

        finally:
            heartbeat_task.cancel()
            logger.info(f"Worker {self.worker_id} shutting down. Completed: {self.jobs_completed}, Failed: {self.jobs_failed}")


def run_worker():
    """Entry point for worker mode."""
    worker = FormAIWorker()
    asyncio.run(worker.run())


if __name__ == "__main__":
    # Can be run directly or via formai_entry.py
    if os.getenv("MODE", "").lower() == "worker" or len(sys.argv) > 1 and sys.argv[1] == "worker":
        run_worker()
    else:
        print("FormAI Worker")
        print("Usage: Set MODE=worker environment variable or run: python worker.py worker")
        print("")
        print("This worker pulls jobs from Redis and processes form automation tasks.")
        print("Typically run inside Docker containers with docker-compose.")
