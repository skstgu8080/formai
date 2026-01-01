"""
FormAI Job Models

Pydantic models for job queue operations.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(BaseModel):
    """A form automation job to be processed by a worker."""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    profile_id: str
    recording_id: str
    target_url: Optional[str] = None  # Optional: override URL from recording
    created_at: datetime = Field(default_factory=datetime.utcnow)
    priority: int = 0  # Higher = more important
    status: str = "pending"
    worker_id: Optional[str] = None
    started_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class JobResult(BaseModel):
    """Result of a completed job."""
    job_id: str
    status: str  # "success", "failed", "processing"
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    download_paths: List[str] = Field(default_factory=list)
    fields_filled: int = 0
    form_submitted: bool = False
    completed_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class WorkerStatus(BaseModel):
    """Status of a worker."""
    worker_id: str
    status: str = "idle"  # idle, busy, offline
    current_job_id: Optional[str] = None
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)
    jobs_completed: int = 0
    jobs_failed: int = 0
    hostname: Optional[str] = None


class JobSubmitRequest(BaseModel):
    """Request to submit a new job."""
    profile_id: str
    recording_id: str
    target_url: Optional[str] = None
    count: int = 1  # Number of times to run this job


class JobStats(BaseModel):
    """Statistics about the job queue."""
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    workers_active: int = 0
    workers_idle: int = 0
