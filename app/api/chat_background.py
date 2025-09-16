"""
Background processing functions for geodata requests.

Separated from main chat module to handle async service orchestration.
"""

import asyncio
from collections.abc import Callable

import structlog

from app.models import Job, JobStatus
from app.services import DataService, ExportService, MetadataService, NLPService, ProcessingService

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

    Orchestrates: NLP → Data → Processing → Metadata → Export services
    Updates job progress with 8 granular stages and creates real ZIP packages.
    """
    job_logger = logger.bind(job_id=job_id)
    job_logger.info("Starting background geodata processing")

    try:
        # Create services
        nlp_service = NLPService()
        data_service = DataService()
        processing_service = ProcessingService()
        metadata_service = MetadataService()
        export_service = ExportService()

        # Get database session
        with session_factory() as session:
            # Get job from database
            job = session.get(Job, job_id)
            if not job:
                job_logger.error("Job not found in database")
                return

            try:
                # Stage 1: Initialize processing (0% → 15%)
                job.status = JobStatus.PROCESSING
                job.progress = 0
                session.add(job)
                session.commit()
                job_logger.info("Job status updated to processing")

                # Stage 2: NLP Service - Parse user request (15%)
                job_logger.info("Starting NLP parsing")
                parsed_request = nlp_service.parse_user_request(user_text)

                job.bezirk = parsed_request.bezirk
                job.datasets = str(parsed_request.datasets) if parsed_request.datasets else None
                job.progress = 15
                session.add(job)
                session.commit()
                job_logger.info(
                    "NLP parsing completed",
                    bezirk=parsed_request.bezirk,
                    datasets=parsed_request.datasets,
                )

                # Stage 3: Data Service - Start acquisition (25%)
                job_logger.info("Starting data acquisition")
                if not parsed_request.bezirk:
                    raise ValueError("No district identified from request")

                job.progress = 25
                session.add(job)
                session.commit()

                datasets = await data_service.fetch_datasets_for_request(
                    parsed_request.bezirk, parsed_request.datasets or []
                )

                # Stage 4: Data acquisition completed (40%)
                job.progress = 40
                session.add(job)
                session.commit()
                job_logger.info("Data acquisition completed", dataset_count=len(datasets))

                # Stage 5: Processing Service - Harmonize data (55%)
                job_logger.info("Starting data harmonization")
                # Extract boundary from datasets for harmonization
                boundary_dataset = next(
                    (d for d in datasets if d["dataset_type"] == "bezirksgrenzen"), None
                )
                if not boundary_dataset:
                    raise ValueError("District boundary not found in datasets")

                # Execute harmonization for data processing (result not used in current implementation)
                await processing_service.harmonize_datasets(
                    datasets, boundary_dataset["geodata"]
                )

                job.progress = 55
                session.add(job)
                session.commit()
                job_logger.info("Data harmonization completed")

                # Stage 6: Metadata Service - Generate report (70%)
                job_logger.info("Starting metadata report generation")
                if not parsed_request.bezirk:
                    raise ValueError("No district for metadata report")

                # Use original datasets for metadata generation (harmonized result is different format)
                metadata_report = metadata_service.create_metadata_report(
                    datasets, parsed_request.bezirk, {"original_request": user_text}
                )

                job.progress = 70
                session.add(job)
                session.commit()
                job_logger.info("Metadata generation completed")

                # Stage 7: Export Service - Start package creation (85%)
                job_logger.info("Starting ZIP package creation")
                job.progress = 85
                session.add(job)
                session.commit()

                # Create actual ZIP package with Export Service
                # Use original datasets for export (since harmonized result has different format)
                package = export_service.create_geodata_package(
                    datasets,
                    metadata_report,
                    parsed_request.bezirk,
                    job_id,
                )

                # Save package to database
                session.add(package)
                session.commit()
                session.refresh(package)

                # Stage 8: Job completed (100%)
                job.mark_completed(package.id)
                job.progress = 100
                session.add(job)
                session.commit()
                job_logger.info(
                    "Package creation completed, job finished",
                    package_id=package.id,
                    file_size_mb=package.get_file_size_mb(),
                )

            except Exception as e:
                job_logger.error("Job processing failed", error=str(e))
                job.mark_failed(f"Processing error: {str(e)}")
                session.add(job)
                session.commit()

    except Exception as e:
        job_logger.error("Background task failed", error=str(e))
