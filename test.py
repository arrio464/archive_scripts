import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Set

from compress import compress_files


class BaseCompressTest(unittest.TestCase):
    """Base test class with common setup and teardown functionality."""

    def setUp(self) -> None:
        """Set up test environment with temporary directories."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.output_dir = Path(tempfile.mkdtemp())
        self.extract_dir = self.output_dir / "extracted"

    def tearDown(self) -> None:
        """Clean up temporary test directories."""
        shutil.rmtree(self.test_dir)
        shutil.rmtree(self.output_dir)

    def create_file(self, file_path: Path, content: str = "test content") -> None:
        """Create a file with given content."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    def extract_archive(self, archive_path: Path) -> None:
        """Extract the archive to the test directory."""
        self.extract_dir.mkdir(exist_ok=True)
        subprocess.run(
            ["7z", "x", str(archive_path), f"-o{self.extract_dir}"],
            check=True,
            capture_output=True,
        )

    def verify_files(self, should_exist: Set[str], should_not_exist: Set[str]) -> None:
        """Verify the existence and non-existence of files."""
        for file_path in should_exist:
            full_path = self.extract_dir / file_path
            self.assertTrue(
                full_path.exists(), f"File should exist but doesn't: {file_path}"
            )

        for file_path in should_not_exist:
            full_path = self.extract_dir / file_path
            self.assertFalse(
                full_path.exists(), f"File should not exist but does: {file_path}"
            )


class TestBasicCompress(BaseCompressTest):
    """Test basic compression functionality with simple .gitignore rules."""

    def setUp(self) -> None:
        """Set up test environment with basic .gitignore configuration."""
        super().setUp()

        gitignore_content = ["*_ignore.txt", "!do_not_ignore.txt", "ignore_dir/**"]
        self.create_file(self.test_dir / ".gitignore", "\n".join(gitignore_content))

        # Create test directory structure
        test_files = {
            "some_file.txt": "",
            "please_ignore.txt": "",
            "do_not_ignore.txt": "",
            "ignore_dir/ignore_file.txt": "",
            "not_ignore_dir/not_ignore_file.txt": "",
        }

        for file_path, content in test_files.items():
            self.create_file(self.test_dir / file_path)

    def test_compress_files(self) -> None:
        """Test basic file compression with .gitignore rules."""
        archive_path = compress_files(self.test_dir, self.output_dir, ".gitignore")
        self.extract_archive(archive_path)

        should_exist = {
            ".gitignore",
            "some_file.txt",
            "do_not_ignore.txt",
            "not_ignore_dir/not_ignore_file.txt",
        }

        should_not_exist = {"please_ignore.txt", "ignore_dir/ignore_file.txt"}

        self.verify_files(should_exist, should_not_exist)


class TestRecursiveGitignore(BaseCompressTest):
    """Test compression with nested .gitignore rules."""

    def setUp(self) -> None:
        """Set up test environment with nested .gitignore configurations."""
        super().setUp()

        # Create .gitignore files
        gitignore_contents = {
            ".gitignore": ["*.root_ignored", "!*.root_force_include"],
            "dir1/.gitignore": ["*.dir1_ignored", "!*.dir1_force_include"],
            "dir1/subdir1/.gitignore": ["*.subdir_ignored"],
        }

        for path, content in gitignore_contents.items():
            self.create_file(self.test_dir / path, "\n".join(content))

        # Create test files
        test_files = [
            "normal.txt",
            "test.root_ignored",
            "test.root_force_include",
            "dir1/normal_dir1.txt",
            "dir1/test.dir1_ignored",
            "dir1/test.dir1_force_include",
            "dir1/test.root_ignored",
            "dir1/subdir1/normal_subdir.txt",
            "dir1/subdir1/test.subdir_ignored",
            "dir1/subdir1/test.dir1_ignored",
            "dir2/normal_dir2.txt",
            "dir2/test.root_ignored",
        ]

        for file_path in test_files:
            self.create_file(self.test_dir / file_path)

    def test_recursive_gitignore(self) -> None:
        """Test compression with nested .gitignore rules."""
        archive_path = compress_files(self.test_dir, self.output_dir, ".gitignore")
        self.extract_archive(archive_path)

        should_exist = {
            "normal.txt",
            "test.root_force_include",
            "dir1/normal_dir1.txt",
            "dir1/test.dir1_force_include",
            "dir1/subdir1/normal_subdir.txt",
            "dir2/normal_dir2.txt",
        }

        should_not_exist = {
            "test.root_ignored",
            "dir1/test.dir1_ignored",
            "dir1/test.root_ignored",
            "dir1/subdir1/test.subdir_ignored",
            "dir1/subdir1/test.dir1_ignored",
            "dir2/test.root_ignored",
        }

        self.verify_files(should_exist, should_not_exist)


if __name__ == "__main__":
    unittest.main()
