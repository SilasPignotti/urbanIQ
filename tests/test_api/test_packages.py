"""
Comprehensive integration tests for Packages API endpoints.

Tests secure ZIP package downloads, file serving, security validation,
download tracking, and error handling with realistic file scenarios.
"""

import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models import Package


class TestPackageDownloadEndpoint:
    """Test cases for GET /api/packages/{package_id} endpoint."""

    def test_package_download_success(self, client: TestClient, temp_zip_file: Path, db_session):
        """Test successful package download with valid ZIP file."""
        package = Package(
            id="download-test-123",
            job_id="job-123",
            file_path=str(temp_zip_file),
            file_size=temp_zip_file.stat().st_size,
            download_count=0,
        )
        db_session.add(package)
        db_session.commit()

        response = client.get(f"/api/packages/{package.id}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers["content-disposition"]
        assert (
            f"filename=geodata_package_{package.id}.zip" in response.headers["content-disposition"]
        )
        assert response.headers["x-package-id"] == package.id
        assert "x-download-count" in response.headers

        # Verify download counter increment
        db_session.refresh(package)
        assert package.download_count == 1

    def test_package_download_nonexistent_package(self, client: TestClient):
        """Test package download with non-existent package ID."""
        response = client.get("/api/packages/nonexistent-package-id")

        assert response.status_code == 404
        error_data = response.json()
        assert "nicht gefunden" in error_data["error"]["message"].lower()

    def test_package_download_nonexistent_file(self, client: TestClient, db_session):
        """Test package download with package record but missing file."""
        package = Package(
            id="missing-file-package",
            job_id="job-456",
            file_path="/nonexistent/path/package.zip",
            file_size=1024,
        )
        db_session.add(package)
        db_session.commit()

        response = client.get(f"/api/packages/{package.id}")

        assert response.status_code == 404
        error_data = response.json()
        assert "nicht gefunden" in error_data["error"]["message"].lower()

    def test_package_download_expired_package(
        self, client: TestClient, temp_zip_file: Path, db_session
    ):
        """Test package download with expired package."""
        from datetime import datetime, timedelta

        # Create expired package
        package = Package(
            id="expired-package-123",
            job_id="job-789",
            file_path=str(temp_zip_file),
            file_size=temp_zip_file.stat().st_size,
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
        )
        db_session.add(package)
        db_session.commit()

        response = client.get(f"/api/packages/{package.id}")

        assert response.status_code == 410
        error_data = response.json()
        assert "abgelaufen" in error_data["error"]["message"].lower()

    def test_package_download_security_validation(self, client: TestClient):
        """Test package download with security-problematic package IDs."""
        malicious_ids = [
            "../../../etc/passwd",
            "package/../../../secret.txt",
            "package///.env",
            "package\\..\\secret",
            "package..package",
            "x" * 300,  # Very long ID
            "",  # Empty ID
        ]

        for malicious_id in malicious_ids:
            response = client.get(f"/api/packages/{malicious_id}")

            # Should return either 403 (security violation) or 404 (not found)
            assert response.status_code in (403, 404, 422)

            if response.status_code == 403:
                error_data = response.json()
                assert "ungültiges paket-format" in error_data["error"]["message"].lower()

    def test_package_download_non_zip_file(
        self, client: TestClient, temp_export_dir: Path, db_session
    ):
        """Test package download with non-ZIP file."""
        # Create a text file instead of ZIP
        text_file = temp_export_dir / "not_a_zip.txt"
        text_file.write_text("This is not a ZIP file")

        package = Package(
            id="not-zip-package",
            job_id="job-not-zip",
            file_path=str(text_file),
            file_size=text_file.stat().st_size,
        )
        db_session.add(package)
        db_session.commit()

        response = client.get(f"/api/packages/{package.id}")

        assert response.status_code == 403
        error_data = response.json()
        assert "ungültiges paket-format" in error_data["error"]["message"].lower()

    def test_package_download_large_file(
        self, client: TestClient, temp_export_dir: Path, db_session
    ):
        """Test package download with large ZIP file."""
        # Create a larger ZIP file
        large_zip = temp_export_dir / "large_package.zip"

        with zipfile.ZipFile(large_zip, "w") as zf:
            # Add multiple files to make it larger
            for i in range(10):
                content = f"Large file content {i}\n" * 1000
                zf.writestr(f"data_{i}.txt", content)

        package = Package(
            id="large-package-123",
            job_id="job-large",
            file_path=str(large_zip),
            file_size=large_zip.stat().st_size,
        )
        db_session.add(package)
        db_session.commit()

        response = client.get(f"/api/packages/{package.id}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert int(response.headers["content-length"]) > 10000

    def test_package_download_concurrent_access(
        self, client: TestClient, temp_zip_file: Path, db_session
    ):
        """Test concurrent package downloads and counter accuracy."""
        package = Package(
            id="concurrent-package",
            job_id="job-concurrent",
            file_path=str(temp_zip_file),
            file_size=temp_zip_file.stat().st_size,
            download_count=0,
        )
        db_session.add(package)
        db_session.commit()

        # Simulate multiple concurrent downloads
        responses = []
        for _ in range(5):
            response = client.get(f"/api/packages/{package.id}")
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200

        # Download count should be accurately incremented
        db_session.refresh(package)
        assert package.download_count == 5

    def test_package_download_headers_validation(
        self, client: TestClient, temp_zip_file: Path, db_session
    ):
        """Test all required headers in package download response."""
        package = Package(
            id="headers-test-package",
            job_id="job-headers",
            file_path=str(temp_zip_file),
            file_size=temp_zip_file.stat().st_size,
            download_count=5,
        )
        db_session.add(package)
        db_session.commit()

        response = client.get(f"/api/packages/{package.id}")

        assert response.status_code == 200

        # Verify all required headers
        headers = response.headers
        assert headers["content-type"] == "application/zip"
        assert "attachment" in headers["content-disposition"]
        assert f"filename=geodata_package_{package.id}.zip" in headers["content-disposition"]
        assert headers["x-package-id"] == package.id
        assert int(headers["x-download-count"]) == 6  # Should be incremented
        assert "cache-control" in headers
        assert int(headers["content-length"]) > 0


class TestPackageSecurityValidation:
    """Test cases for security validation in package downloads."""

    def test_package_id_length_validation(self, client: TestClient):
        """Test package ID length validation."""
        # Too short
        response = client.get("/api/packages/short")
        assert response.status_code in (403, 404)

        # Very long
        long_id = "a" * 300
        response = client.get(f"/api/packages/{long_id}")
        assert response.status_code in (403, 404, 422)

    def test_package_id_character_validation(self, client: TestClient):
        """Test package ID character validation."""
        invalid_chars = ["../", "//", "\\", ":", "*", "?", "<", ">", "|"]

        for char in invalid_chars:
            package_id = f"package{char}test"
            response = client.get(f"/api/packages/{package_id}")
            assert response.status_code in (403, 404, 422)

    def test_path_traversal_prevention(self, client: TestClient, db_session):
        """Test path traversal attack prevention."""
        # Create package with path traversal in file_path
        package = Package(
            id="traversal-test",
            job_id="job-traversal",
            file_path="../../../etc/passwd",  # Malicious path
            file_size=1024,
        )
        db_session.add(package)
        db_session.commit()

        response = client.get(f"/api/packages/{package.id}")

        # Should safely handle this as file not found
        assert response.status_code == 404

    def test_file_type_validation(self, client: TestClient, temp_export_dir: Path, db_session):
        """Test file type validation beyond ZIP extension."""
        # Create file with .zip extension but not actually a ZIP
        fake_zip = temp_export_dir / "fake.zip"
        fake_zip.write_text("This is not a real ZIP file")

        package = Package(
            id="fake-zip-package",
            job_id="job-fake-zip",
            file_path=str(fake_zip),
            file_size=fake_zip.stat().st_size,
        )
        db_session.add(package)
        db_session.commit()

        response = client.get(f"/api/packages/{package.id}")

        # Should detect this is not a real ZIP and reject
        assert response.status_code == 403


class TestPackageErrorHandling:
    """Test cases for error handling in package downloads."""

    def test_package_database_error(self, client: TestClient):
        """Test package download with database error."""
        with patch("app.api.deps.get_session") as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            response = client.get("/api/packages/any-package-id")
            assert response.status_code == 500

    def test_package_file_permission_error(self, client: TestClient, db_session):
        """Test package download with file permission issues."""
        # Create package pointing to system file (should not be accessible)
        package = Package(
            id="permission-test",
            job_id="job-permission",
            file_path="/root/secret.zip",  # Should not be accessible
            file_size=1024,
        )
        db_session.add(package)
        db_session.commit()

        response = client.get(f"/api/packages/{package.id}")

        assert response.status_code == 404  # Should be treated as not found for security

    def test_package_corrupted_database_record(self, client: TestClient, db_session):
        """Test package download with corrupted database record."""
        # Create package with invalid data (would fail validation)
        # package = Package(
        #     id="corrupted-package",
        #     job_id="job-corrupted",
        #     file_path=None,  # Invalid: should not be None
        #     file_size=-1,  # Invalid: negative size
        # )

        # Bypass validation by directly inserting
        db_session.execute(
            "INSERT INTO packages (id, job_id, file_path, file_size) VALUES (?, ?, ?, ?)",
            ("corrupted-package", "job-corrupted", None, -1),
        )
        db_session.commit()

        response = client.get("/api/packages/corrupted-package")

        assert response.status_code in (404, 500)


class TestPackagePerformance:
    """Test cases for package download performance."""

    def test_package_download_response_time(
        self, client: TestClient, temp_zip_file: Path, db_session
    ):
        """Test package download response time for small files."""
        import time

        package = Package(
            id="perf-test-package",
            job_id="job-perf",
            file_path=str(temp_zip_file),
            file_size=temp_zip_file.stat().st_size,
        )
        db_session.add(package)
        db_session.commit()

        start_time = time.time()
        response = client.get(f"/api/packages/{package.id}")
        response_time = time.time() - start_time

        assert response.status_code == 200
        assert response_time < 3.0  # Should download quickly for small files

    def test_package_download_memory_efficiency(
        self, client: TestClient, temp_export_dir: Path, db_session
    ):
        """Test memory efficiency for larger file downloads."""
        # Create moderately large ZIP file
        large_zip = temp_export_dir / "memory_test.zip"

        with zipfile.ZipFile(large_zip, "w") as zf:
            # Add content to make it a few MB
            content = "Test data for memory efficiency testing\n" * 10000
            for i in range(20):
                zf.writestr(f"test_file_{i}.txt", content)

        package = Package(
            id="memory-test-package",
            job_id="job-memory",
            file_path=str(large_zip),
            file_size=large_zip.stat().st_size,
        )
        db_session.add(package)
        db_session.commit()

        # Download should work without memory issues
        response = client.get(f"/api/packages/{package.id}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

    def test_package_download_concurrent_load(
        self, client: TestClient, temp_zip_file: Path, db_session
    ):
        """Test package download under concurrent load."""
        package = Package(
            id="load-test-package",
            job_id="job-load",
            file_path=str(temp_zip_file),
            file_size=temp_zip_file.stat().st_size,
        )
        db_session.add(package)
        db_session.commit()

        # Simulate concurrent downloads
        import threading
        import time

        results = []

        def download_package():
            start = time.time()
            response = client.get(f"/api/packages/{package.id}")
            end = time.time()
            results.append((response.status_code, end - start))

        # Create multiple threads for concurrent access
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=download_package)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # Verify all succeeded
        assert len(results) == 10
        assert all(status == 200 for status, _ in results)
        assert all(response_time < 5.0 for _, response_time in results)


class TestPackageDownloadTracking:
    """Test cases for download tracking and statistics."""

    def test_download_counter_accuracy(self, client: TestClient, temp_zip_file: Path, db_session):
        """Test download counter accuracy across multiple downloads."""
        package = Package(
            id="counter-test-package",
            job_id="job-counter",
            file_path=str(temp_zip_file),
            file_size=temp_zip_file.stat().st_size,
            download_count=10,  # Start with existing downloads
        )
        db_session.add(package)
        db_session.commit()

        # Download multiple times
        for i in range(5):
            response = client.get(f"/api/packages/{package.id}")
            assert response.status_code == 200

            # Check counter in header
            expected_count = 11 + i  # 10 initial + current download
            assert int(response.headers["x-download-count"]) == expected_count

        # Verify final count in database
        db_session.refresh(package)
        assert package.download_count == 15

    def test_download_counter_isolation(self, client: TestClient, temp_zip_file: Path, db_session):
        """Test download counter isolation between packages."""
        package1 = Package(
            id="isolation-package-1",
            job_id="job-isolation-1",
            file_path=str(temp_zip_file),
            file_size=temp_zip_file.stat().st_size,
            download_count=0,
        )

        package2 = Package(
            id="isolation-package-2",
            job_id="job-isolation-2",
            file_path=str(temp_zip_file),
            file_size=temp_zip_file.stat().st_size,
            download_count=0,
        )

        db_session.add_all([package1, package2])
        db_session.commit()

        # Download from package1 multiple times
        for _ in range(3):
            response = client.get(f"/api/packages/{package1.id}")
            assert response.status_code == 200

        # Download from package2 once
        response = client.get(f"/api/packages/{package2.id}")
        assert response.status_code == 200

        # Verify independent counters
        db_session.refresh(package1)
        db_session.refresh(package2)

        assert package1.download_count == 3
        assert package2.download_count == 1
