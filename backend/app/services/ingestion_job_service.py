import uuid
from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from backend.app.models import AuditLog, IngestionJob


class IngestionJobService:
    SUPPORTED_SOURCES = {"aws_cur", "azure_cost", "gcp_billing", "kubernetes", "file_upload", "openai_billing"}

    @staticmethod
    def list_jobs(db: Session, tenant_id: str) -> List[Dict]:
        jobs = (
            db.query(IngestionJob)
            .filter(IngestionJob.tenant_id == tenant_id)
            .order_by(IngestionJob.created_at.desc())
            .all()
        )
        return [
            {
                "id": j.id,
                "source_type": j.source_type,
                "source_ref": j.source_ref,
                "status": j.status,
                "retry_count": j.retry_count,
                "max_retries": j.max_retries,
                "processed_items": j.processed_items,
                "error_message": j.error_message,
                "started_at": j.started_at.strftime("%Y-%m-%d %H:%M") if j.started_at else None,
                "completed_at": j.completed_at.strftime("%Y-%m-%d %H:%M") if j.completed_at else None,
                "created_at": j.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for j in jobs
        ]

    @staticmethod
    def create_job(
        db: Session,
        tenant_id: str,
        username: str,
        source_type: str,
        source_ref: str = None,
        max_retries: int = 3,
    ) -> Dict:
        if source_type not in IngestionJobService.SUPPORTED_SOURCES:
            raise ValueError(f"Source non supportee: {source_type}")

        job = IngestionJob(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            source_type=source_type,
            source_ref=source_ref,
            status="Queued",
            retry_count=0,
            max_retries=max(1, min(max_retries, 10)),
            metadata_json={"created_by": username},
            created_at=datetime.utcnow(),
        )
        db.add(job)
        db.add(
            AuditLog(
                tenant_id=tenant_id,
                action="ingestion_job_created",
                user=username,
                resource_type="ingestion_job",
                resource_id=job.id,
                details=f"source_type={source_type};source_ref={source_ref}",
                timestamp=datetime.utcnow(),
            )
        )
        db.commit()
        return {"success": True, "job_id": job.id, "status": job.status}

    @staticmethod
    def run_job(db: Session, tenant_id: str, username: str, job_id: str) -> Dict:
        job = db.query(IngestionJob).filter(IngestionJob.tenant_id == tenant_id, IngestionJob.id == job_id).first()
        if not job:
            return {"success": False, "message": "Job introuvable."}

        job.status = "Running"
        job.started_at = datetime.utcnow()
        job.error_message = None
        db.commit()

        # Simulation d'ingestion déterministe + échec/rattrapage pour tester retry.
        has_transient_failure = job.source_type in {"openai_billing", "file_upload"} and job.retry_count == 0
        if has_transient_failure:
            job.status = "Failed"
            job.retry_count += 1
            job.error_message = "Transient source timeout. Retry required."
            db.commit()
            return {
                "success": False,
                "job_id": job.id,
                "status": job.status,
                "retry_count": job.retry_count,
                "error_message": job.error_message,
            }

        processed_items = 250 if job.source_type in {"aws_cur", "azure_cost", "gcp_billing"} else 80
        job.status = "Succeeded"
        job.processed_items = processed_items
        job.completed_at = datetime.utcnow()
        db.add(
            AuditLog(
                tenant_id=tenant_id,
                action="ingestion_job_succeeded",
                user=username,
                resource_type="ingestion_job",
                resource_id=job.id,
                details=f"processed_items={processed_items}",
                timestamp=datetime.utcnow(),
            )
        )
        db.commit()
        return {
            "success": True,
            "job_id": job.id,
            "status": job.status,
            "processed_items": processed_items,
            "completed_at": job.completed_at.strftime("%Y-%m-%d %H:%M"),
        }

    @staticmethod
    def retry_job(db: Session, tenant_id: str, username: str, job_id: str) -> Dict:
        job = db.query(IngestionJob).filter(IngestionJob.tenant_id == tenant_id, IngestionJob.id == job_id).first()
        if not job:
            return {"success": False, "message": "Job introuvable."}
        if job.retry_count >= job.max_retries:
            return {"success": False, "message": "Limite de retries atteinte."}

        db.add(
            AuditLog(
                tenant_id=tenant_id,
                action="ingestion_job_retry_requested",
                user=username,
                resource_type="ingestion_job",
                resource_id=job.id,
                details=f"retry_count={job.retry_count}",
                timestamp=datetime.utcnow(),
            )
        )
        db.commit()
        return IngestionJobService.run_job(db, tenant_id, username, job_id)
