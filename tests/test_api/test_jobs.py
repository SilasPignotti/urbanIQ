"""
Comprehensive integration tests for Jobs API endpoints.

Tests job status tracking, listing, lifecycle management, and real-time progress monitoring
with database integration and error handling validation.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models import Job, JobStatus, Package


class TestJobStatusEndpoint:
    """Test cases for GET /api/jobs/status/{job_id} endpoint."""

    def test_job_status_endpoint_pending_job(self, client: TestClient, sample_job: Job):
        """Test job status endpoint with pending job."""
        response = client.get(f"/api/jobs/status/{sample_job.id}")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["job_id"] == sample_job.id
        assert data["status"] == "pending"
        assert data["progress"] == 0
        assert "created_at" in data
        assert data["completed_at"] is None
        assert data["download_url"] is None
        assert "bezirk" in data
        assert "datasets" in data

    def test_job_status_endpoint_completed_job(self, client: TestClient, completed_job: Job):
        """Test job status endpoint with completed job and package."""
        response = client.get(f"/api/jobs/status/{completed_job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["job_id"] == completed_job.id
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert data["completed_at"] is not None
        assert data["download_url"] is not None
        assert "/api/packages/" in data["download_url"]

    def test_job_status_endpoint_processing_job(self, client: TestClient, db_session):
        """Test job status endpoint with processing job."""
        job = Job(
            id="processing-job-123",
            request_text="Friedrichshain buildings analysis",
            bezirk="Friedrichshain-Kreuzberg",
            datasets='["gebaeude"]',
            status=JobStatus.PROCESSING,
            progress=65,
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/jobs/status/{job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "processing"
        assert data["progress"] == 65
        assert data["download_url"] is None

    def test_job_status_endpoint_failed_job(self, client: TestClient, db_session):
        """Test job status endpoint with failed job."""
        job = Job(
            id="failed-job-456",
            request_text="Invalid request",
            bezirk="Unknown",
            datasets="[]",
            status=JobStatus.FAILED,
            progress=25,
            error_message="NLP parsing failed: district not recognized",
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/jobs/status/{job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "failed"
        assert data["progress"] == 25
        assert data["error_message"] is not None
        assert "not recognized" in data["error_message"]
        assert data["download_url"] is None

    def test_job_status_endpoint_nonexistent_job(self, client: TestClient):
        """Test job status endpoint with non-existent job ID."""
        response = client.get("/api/jobs/status/nonexistent-job-id")

        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["detail"].lower()

    def test_job_status_endpoint_invalid_job_id_format(self, client: TestClient):
        """Test job status endpoint with invalid job ID format."""
        invalid_ids = [
            "",
            "short",
            "invalid/chars",
            "very-very-very-long-invalid-job-id-that-exceeds-limits",
        ]

        for invalid_id in invalid_ids:
            response = client.get(f"/api/jobs/status/{invalid_id}")
            # Should either be 404 or 422 depending on validation
            assert response.status_code in (404, 422)

    def test_job_status_endpoint_with_runtime_stats(self, client: TestClient, db_session):
        """Test job status endpoint with runtime statistics."""
        runtime_stats = {
            "processing_time_seconds": 180,
            "datasets_processed": 2,
            "total_features": 1250,
            "data_quality_score": 0.94,
            "spatial_coverage_percent": 97.5,
        }

        job = Job(
            id="stats-job-789",
            request_text="Neukölln comprehensive analysis",
            bezirk="Neukölln",
            datasets='["gebaeude", "oepnv_haltestellen"]',
            status=JobStatus.COMPLETED,
            progress=100,
            runtime_stats=runtime_stats,
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/jobs/status/{job.id}")

        assert response.status_code == 200
        data = response.json()

        assert "runtime_stats" in data
        stats = data["runtime_stats"]
        assert stats["processing_time_seconds"] == 180
        assert stats["total_features"] == 1250
        assert stats["data_quality_score"] == 0.94


class TestJobListingEndpoint:
    """Test cases for GET /api/jobs/ endpoint."""

    def test_job_listing_endpoint_default(self, client: TestClient, db_session):
        """Test job listing endpoint with default parameters."""
        # Create multiple test jobs
        jobs = [
            Job(
                id=f"list-job-{i}",
                request_text=f"Test request {i}",
                bezirk="Pankow",
                datasets='["gebaeude"]',
                status=JobStatus.COMPLETED if i % 2 == 0 else JobStatus.PENDING,
                progress=100 if i % 2 == 0 else 0,
                created_at=datetime.now() - timedelta(hours=i),
            )
            for i in range(5)
        ]

        for job in jobs:
            db_session.add(job)
        db_session.commit()

        response = client.get("/api/jobs/")

        assert response.status_code == 200
        data = response.json()

        assert "jobs" in data
        assert "total" in data
        assert len(data["jobs"]) <= 10  # Default limit
        assert data["total"] >= 5

        # Verify jobs are ordered by creation time (newest first)
        job_times = [job["created_at"] for job in data["jobs"]]
        assert job_times == sorted(job_times, reverse=True)

    def test_job_listing_endpoint_with_limit(self, client: TestClient, db_session):
        """Test job listing endpoint with custom limit."""
        # Create more jobs than limit
        jobs = [
            Job(
                id=f"limited-job-{i}",
                request_text=f"Limited request {i}",
                bezirk="Mitte",
                datasets='["gebaeude"]',
                status=JobStatus.COMPLETED,
                progress=100,
            )
            for i in range(15)
        ]

        for job in jobs:
            db_session.add(job)
        db_session.commit()

        response = client.get("/api/jobs/?limit=5")

        assert response.status_code == 200
        data = response.json()

        assert len(data["jobs"]) == 5
        assert data["total"] >= 15

    def test_job_listing_endpoint_large_limit(self, client: TestClient, db_session):
        """Test job listing endpoint with large limit."""
        response = client.get("/api/jobs/?limit=1000")

        assert response.status_code == 200
        data = response.json()
        # Should be capped at reasonable limit (e.g., 100)
        assert len(data["jobs"]) <= 100

    def test_job_listing_endpoint_invalid_limit(self, client: TestClient):
        """Test job listing endpoint with invalid limit values."""
        invalid_limits = [-1, 0, "invalid", ""]

        for limit in invalid_limits:
            response = client.get(f"/api/jobs/?limit={limit}")
            assert response.status_code == 422

    def test_job_listing_endpoint_empty_database(self, client: TestClient):
        """Test job listing endpoint with empty database."""
        response = client.get("/api/jobs/")

        assert response.status_code == 200
        data = response.json()

        assert data["jobs"] == []
        assert data["total"] == 0

    def test_job_listing_endpoint_mixed_statuses(self, client: TestClient, db_session):
        """Test job listing endpoint with jobs in various statuses."""
        statuses = [JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.COMPLETED, JobStatus.FAILED]
        jobs = [
            Job(
                id=f"mixed-job-{i}",
                request_text=f"Mixed status request {i}",
                bezirk="Charlottenburg-Wilmersdorf",
                datasets='["gebaeude"]',
                status=status,
                progress=25 * i if status != JobStatus.FAILED else 10,
                error_message="Test error" if status == JobStatus.FAILED else None,
            )
            for i, status in enumerate(statuses)
        ]

        for job in jobs:
            db_session.add(job)
        db_session.commit()

        response = client.get("/api/jobs/")

        assert response.status_code == 200
        data = response.json()

        assert len(data["jobs"]) == 4
        statuses_returned = [job["status"] for job in data["jobs"]]
        assert "pending" in statuses_returned
        assert "processing" in statuses_returned
        assert "completed" in statuses_returned
        assert "failed" in statuses_returned


class TestJobDatasetParsing:
    """Test cases for job dataset JSON parsing in responses."""

    def test_job_with_valid_datasets_json(self, client: TestClient, db_session):
        """Test job status with valid datasets JSON."""
        job = Job(
            id="json-job-123",
            request_text="Spandau analysis",
            bezirk="Spandau",
            datasets='["gebaeude", "oepnv_haltestellen"]',
            status=JobStatus.COMPLETED,
            progress=100,
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/jobs/status/{job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["datasets"] == ["gebaeude", "oepnv_haltestellen"]

    def test_job_with_empty_datasets(self, client: TestClient, db_session):
        """Test job status with empty datasets."""
        job = Job(
            id="empty-datasets-job",
            request_text="Invalid request",
            bezirk="Unknown",
            datasets="[]",
            status=JobStatus.FAILED,
            progress=0,
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/jobs/status/{job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["datasets"] == []

    def test_job_with_single_dataset(self, client: TestClient, db_session):
        """Test job status with single dataset."""
        job = Job(
            id="single-dataset-job",
            request_text="Reinickendorf buildings only",
            bezirk="Reinickendorf",
            datasets='["gebaeude"]',
            status=JobStatus.PROCESSING,
            progress=50,
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/jobs/status/{job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["datasets"] == ["gebaeude"]


class TestJobsErrorHandling:
    """Test cases for error handling in jobs endpoints."""

    def test_jobs_database_error(self, client: TestClient):
        """Test jobs endpoints with database error."""
        with patch("app.api.deps.get_session") as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            response = client.get("/api/jobs/status/any-job-id")
            assert response.status_code == 500

            response = client.get("/api/jobs/")
            assert response.status_code == 500

    def test_job_status_with_sql_injection_attempt(self, client: TestClient):
        """Test job status endpoint with SQL injection attempt."""
        malicious_id = "'; DROP TABLE jobs; --"
        response = client.get(f"/api/jobs/status/{malicious_id}")

        # Should handle gracefully (404 or validation error)
        assert response.status_code in (404, 422)

    def test_jobs_response_headers(self, client: TestClient, sample_job: Job):
        """Test correct response headers for jobs endpoints."""
        response = client.get(f"/api/jobs/status/{sample_job.id}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        response = client.get("/api/jobs/")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"


class TestJobsPerformance:
    """Test cases for jobs endpoints performance."""

    def test_job_status_response_time(self, client: TestClient, sample_job: Job):
        """Test job status endpoint response time."""
        import time

        start_time = time.time()
        response = client.get(f"/api/jobs/status/{sample_job.id}")
        response_time = time.time() - start_time

        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second

    def test_job_listing_with_large_dataset(self, client: TestClient, db_session):
        """Test job listing performance with large number of jobs."""
        # Create many jobs
        jobs = [
            Job(
                id=f"perf-job-{i:04d}",
                request_text=f"Performance test request {i}",
                bezirk="Lichtenberg",
                datasets='["gebaeude"]',
                status=JobStatus.COMPLETED,
                progress=100,
                created_at=datetime.now() - timedelta(minutes=i),
            )
            for i in range(100)
        ]

        for job in jobs:
            db_session.add(job)
        db_session.commit()

        import time

        start_time = time.time()
        response = client.get("/api/jobs/?limit=50")
        response_time = time.time() - start_time

        assert response.status_code == 200
        assert response_time < 2.0  # Should respond within 2 seconds
        assert len(response.json()["jobs"]) == 50


class TestJobDownloadURLGeneration:
    """Test cases for download URL generation in job responses."""

    def test_completed_job_with_package_download_url(self, client: TestClient, db_session):
        """Test download URL generation for completed job with package."""
        job = Job(
            id="download-job-123",
            request_text="Tempelhof analysis",
            bezirk="Tempelhof-Schöneberg",
            datasets='["gebaeude"]',
            status=JobStatus.COMPLETED,
            progress=100,
        )
        db_session.add(job)
        db_session.commit()

        package = Package(
            id="download-package-123",
            job_id=job.id,
            file_path="/tmp/test_package.zip",
            file_size=1024,
        )
        db_session.add(package)
        db_session.commit()

        response = client.get(f"/api/jobs/status/{job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["download_url"] is not None
        assert f"/api/packages/{package.id}" in data["download_url"]

    def test_completed_job_without_package_no_download_url(self, client: TestClient, db_session):
        """Test that completed job without package has no download URL."""
        job = Job(
            id="no-package-job",
            request_text="Steglitz analysis",
            bezirk="Steglitz-Zehlendorf",
            datasets='["gebaeude"]',
            status=JobStatus.COMPLETED,
            progress=100,
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/jobs/status/{job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["download_url"] is None

    def test_processing_job_no_download_url(self, client: TestClient, db_session):
        """Test that processing job has no download URL."""
        job = Job(
            id="processing-no-url-job",
            request_text="Marzahn analysis",
            bezirk="Marzahn-Hellersdorf",
            datasets='["gebaeude"]',
            status=JobStatus.PROCESSING,
            progress=75,
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/jobs/status/{job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["download_url"] is None
