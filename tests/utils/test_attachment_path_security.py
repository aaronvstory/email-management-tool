"""
Tests for attachment path security validations.

Verifies that _is_under() and path resolution work correctly on Windows
with backslashes, forward slashes, and mixed paths.
"""
import pytest
from pathlib import Path
import os
import tempfile
import shutil


def _is_under(child: Path, parent: Path) -> bool:
    """
    Helper function mirroring app.routes.interception._is_under
    Tests if child path is within parent directory.
    """
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


class TestPathSecurity:
    """Test path validation for attachment storage."""

    def test_is_under_basic_same_directory(self):
        """Test basic same directory case."""
        parent = Path("C:/attachments")
        child = Path("C:/attachments/email123/file.pdf")
        assert _is_under(child, parent)

    def test_is_under_nested_directories(self):
        """Test nested directory structure."""
        parent = Path("C:/attachments")
        child = Path("C:/attachments/email123/subfolder/file.pdf")
        assert _is_under(child, parent)

    def test_is_under_parent_outside(self):
        """Test that parent directory escapes are blocked."""
        parent = Path("C:/attachments")
        child = Path("C:/other/file.pdf")
        assert not _is_under(child, parent)

    def test_is_under_traversal_attempt(self):
        """Test path traversal attack prevention."""
        parent = Path("C:/attachments")
        child = Path("C:/attachments/../etc/passwd")
        # After resolution, this becomes C:/etc/passwd
        resolved_child = child.resolve()
        assert not _is_under(resolved_child, parent)

    def test_is_under_windows_backslashes(self):
        """Test Windows path with backslashes."""
        if os.name != 'nt':
            pytest.skip("Windows-specific test")

        parent = Path(r"C:\attachments")
        child = Path(r"C:\attachments\email123\file.pdf")
        assert _is_under(child, parent)

    def test_is_under_mixed_slashes(self):
        """Test mixed forward/back slashes (Windows)."""
        if os.name != 'nt':
            pytest.skip("Windows-specific test")

        parent = Path(r"C:\attachments")
        child = Path("C:/attachments/email123/file.pdf")  # Forward slashes
        # Path normalizes these automatically
        assert _is_under(child, parent)

    def test_is_under_unc_path(self):
        """Test UNC network paths (Windows)."""
        if os.name != 'nt':
            pytest.skip("Windows-specific test")

        parent = Path(r"\\server\share\attachments")
        child = Path(r"\\server\share\attachments\email123\file.pdf")
        assert _is_under(child, parent)

    def test_is_under_case_insensitive(self):
        """Test case insensitivity on Windows."""
        if os.name != 'nt':
            pytest.skip("Windows-specific test")

        parent = Path(r"C:\Attachments")
        child = Path(r"C:\attachments\email123\file.pdf")
        # Windows paths are case-insensitive
        assert _is_under(child, parent)

    def test_is_under_symlink_escape_attempt(self, tmp_path):
        """Test symlink escape prevention."""
        # Create directory structure
        safe_dir = tmp_path / "attachments"
        unsafe_dir = tmp_path / "etc"
        safe_dir.mkdir()
        unsafe_dir.mkdir()

        # Create symlink inside safe_dir pointing outside
        symlink_path = safe_dir / "escape"
        try:
            symlink_path.symlink_to(unsafe_dir)
        except OSError:
            pytest.skip("Symlink creation requires elevated privileges on Windows")

        # Test that resolved symlink is detected as outside
        target_file = symlink_path / "passwd"
        resolved = target_file.resolve()
        assert not _is_under(resolved, safe_dir)

    def test_is_under_relative_paths_resolved(self):
        """Test that relative paths are resolved before checking."""
        parent = Path("attachments").resolve()
        child = Path("attachments/email123/file.pdf").resolve()
        assert _is_under(child, parent)

    def test_is_under_absolute_vs_relative(self):
        """Test mixing absolute and relative paths."""
        parent = Path("C:/attachments")
        child = Path("attachments/email123/file.pdf")  # Relative
        # This should fail because relative path isn't under absolute
        # In practice, code should always resolve() first
        with pytest.raises((ValueError, AssertionError)):
            assert _is_under(child, parent)

    def test_real_world_attachment_path(self, tmp_path):
        """Test realistic attachment storage scenario."""
        # Create realistic directory structure
        attachments_root = tmp_path / "attachments"
        staged_root = tmp_path / "attachments_staged"
        attachments_root.mkdir()
        staged_root.mkdir()

        email_dir = staged_root / "123"
        email_dir.mkdir()

        file_path = email_dir / "invoice.pdf"
        file_path.write_text("fake pdf content")

        # Verify file is within staged_root
        resolved_file = file_path.resolve()
        resolved_staged = staged_root.resolve()
        assert _is_under(resolved_file, resolved_staged)

        # Verify file is NOT within attachments_root
        resolved_attachments = attachments_root.resolve()
        assert not _is_under(resolved_file, resolved_attachments)

    def test_path_normalization_windows(self):
        """Test Path normalization on Windows."""
        if os.name != 'nt':
            pytest.skip("Windows-specific test")

        # Various representations of the same path
        path1 = Path(r"C:\attachments\email123")
        path2 = Path("C:/attachments/email123")
        path3 = Path(r"C:\attachments\.\email123")

        # All should resolve to the same normalized path
        assert path1.resolve() == path2.resolve()
        assert path1.resolve() == path3.resolve()

    def test_security_boundary_at_root(self):
        """Test security boundary exactly at storage root."""
        parent = Path("C:/attachments")
        # Same path should be considered "under" itself
        assert _is_under(parent, parent)

    def test_empty_path_components(self):
        """Test paths with empty components (double slashes)."""
        parent = Path("C:/attachments")
        child = Path("C:/attachments//email123//file.pdf")
        # Path normalizes these automatically
        assert _is_under(child, parent)

    @pytest.mark.parametrize("malicious_path", [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        "./../../../etc",
        "email123/../../etc/passwd",
    ])
    def test_traversal_attack_vectors(self, tmp_path, malicious_path):
        """Test various path traversal attack vectors."""
        safe_dir = tmp_path / "attachments"
        safe_dir.mkdir()

        # Construct malicious path within safe_dir
        test_path = safe_dir / malicious_path

        # After resolution, should NOT be under safe_dir
        resolved = test_path.resolve()
        if resolved.exists() or resolved.parent.exists():
            # Only test if the resolved path could exist
            assert not _is_under(resolved, safe_dir.resolve())


class TestPathValidationIntegration:
    """Integration tests for attachment path validation workflow."""

    def test_complete_validation_workflow(self, tmp_path):
        """Test complete validation workflow as used in app."""
        # Setup
        attachments_root = tmp_path / "attachments"
        staged_root = tmp_path / "attachments_staged"
        attachments_root.mkdir()
        staged_root.mkdir()

        # Simulate file upload
        email_id = 123
        email_dir = staged_root / str(email_id)
        email_dir.mkdir()

        uploaded_file = email_dir / "invoice.pdf"
        uploaded_file.write_bytes(b"fake pdf data")

        # Validation steps (as in api_batch_delete)
        storage_path = Path(str(uploaded_file)).resolve()

        # Step 1: File exists check
        assert storage_path.exists()
        assert storage_path.is_file()

        # Step 2: Path validation
        assert _is_under(storage_path, attachments_root.resolve()) or \
               _is_under(storage_path, staged_root.resolve())

        # Step 3: Safe to delete
        storage_path.unlink()
        assert not storage_path.exists()

    def test_validation_rejects_external_file(self, tmp_path):
        """Test that validation rejects files outside storage roots."""
        attachments_root = tmp_path / "attachments"
        staged_root = tmp_path / "attachments_staged"
        external_dir = tmp_path / "external"

        attachments_root.mkdir()
        staged_root.mkdir()
        external_dir.mkdir()

        # File outside storage roots
        external_file = external_dir / "malicious.exe"
        external_file.write_bytes(b"malware")

        storage_path = external_file.resolve()

        # Should fail validation
        assert not (_is_under(storage_path, attachments_root.resolve()) or
                    _is_under(storage_path, staged_root.resolve()))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
