"""
Background processing functions for geodata requests.

Separated from main chat module to handle async service orchestration.
"""

import asyncio
from collections.abc import Callable

import structlog

from app.models import Job, JobStatus
from app.services import DataService, MetadataService, NLPService, ProcessingService

logger = structlog.get_logger("urbaniq.api.chat.background")


def process_geodata_request_sync(job_id: str, user_text: str, session_factory: Callable) -> None:
    """
    Background task wrapper for async geodata processing.

    This wrapper handles the async event loop for services that require it.
    """
    asyncio.run(_async_process_geodata_request(job_id, user_text, session_factory))


async def _async_process_geodata_request(
    job_id: str, user_text: str, session_factory: Callable
) -> None:
    """
    Async background task to process geodata request through service chain.

    Orchestrates: NLP → Data → Processing → Metadata services
    Updates job progress and status in database.
    """
    job_logger = logger.bind(job_id=job_id)
    job_logger.info("Starting background geodata processing")

    try:
        # Create services
        nlp_service = NLPService()
        data_service = DataService()
        processing_service = ProcessingService()
        metadata_service = MetadataService()

        # Get database session
        with session_factory() as session:
            # Get job from database
            job = session.get(Job, job_id)
            if not job:
                job_logger.error("Job not found in database")
                return

            try:
                # Update to processing status
                job.status = JobStatus.PROCESSING
                job.progress = 0
                session.add(job)
                session.commit()
                job_logger.info("Job status updated to processing")

                # Step 1: NLP Service - Parse user request
                job_logger.info("Starting NLP parsing")
                parsed_request = nlp_service.parse_user_request(user_text)

                job.bezirk = parsed_request.bezirk
                job.datasets = str(parsed_request.datasets) if parsed_request.datasets else None
                job.progress = 25
                session.add(job)
                session.commit()
                job_logger.info(
                    "NLP parsing completed",
                    bezirk=parsed_request.bezirk,
                    datasets=parsed_request.datasets,
                )

                # Step 2: Data Service - Fetch datasets
                job_logger.info("Starting data acquisition")
                if not parsed_request.bezirk:
                    raise ValueError("No district identified from request")

                datasets = await data_service.fetch_datasets_for_request(
                    parsed_request.bezirk, parsed_request.datasets or []
                )

                job.progress = 50
                session.add(job)
                session.commit()
                job_logger.info("Data acquisition completed", dataset_count=len(datasets))

                # Step 3: Processing Service - Harmonize data
                job_logger.info("Starting data harmonization")
                # Extract boundary from datasets for harmonization
                boundary_dataset = next(
                    (d for d in datasets if d["dataset_type"] == "bezirksgrenzen"), None
                )
                if not boundary_dataset:
                    raise ValueError("District boundary not found in datasets")

                await processing_service.harmonize_datasets(datasets, boundary_dataset["geodata"])

                job.progress = 75
                session.add(job)
                session.commit()
                job_logger.info("Data harmonization completed")

                # Step 4: Metadata Service - Generate report
                job_logger.info("Starting metadata report generation")
                if not parsed_request.bezirk:
                    raise ValueError("No district for metadata report")

                metadata_service.create_metadata_report(
                    datasets, parsed_request.bezirk, {"original_request": user_text}
                )

                job.progress = 100
                # TODO: In Step 10, create actual ZIP package and set result_package_id
                # For now, just mark as completed
                job.mark_completed("placeholder-package-id")
                session.add(job)
                session.commit()
                job_logger.info("Metadata generation completed, job finished")

            except Exception as e:
                job_logger.error("Job processing failed", error=str(e))
                job.mark_failed(f"Processing error: {str(e)}")
                session.add(job)
                session.commit()

    except Exception as e:
        job_logger.error("Background task failed", error=str(e))
