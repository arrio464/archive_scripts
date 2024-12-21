import os
import shutil
import subprocess
import tempfile
import unittest

from compress import compress_files


class TestCompress(unittest.TestCase):
    def setUp(self):
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()

        with open(f"{self.test_dir}/.gitignore", "w") as f:
            f.write("*_ignore.txt\n")
            f.write("!do_not_ignore.txt\n")
            f.write("ignore_dir/**\n")

        for directory in ["ignore_dir", "not_ignore_dir"]:
            os.makedirs(f"{self.test_dir}/{directory}")

        for name in [
            "some_file.txt",
            "please_ignore.txt",
            "do_not_ignore.txt",
            "ignore_dir/ignore_file.txt",
            "not_ignore_dir/not_ignore_file.txt",
        ]:
            with open(f"{self.test_dir}/{name}", "w"):
                pass

    def tearDown(self):
        # Remove the temporary directory after the test
        shutil.rmtree(self.test_dir)
        shutil.rmtree(self.output_dir)

    def test_compress_files(self):
        archive_path = compress_files(self.test_dir, self.output_dir)

        subprocess.run(["7z", "x", archive_path, f"-o{self.output_dir}"], check=True)

        result = []
        for root, dirs, files in os.walk(self.output_dir):
            for name in files:
                result.append(name)

        # fmt: off
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, ".gitignore")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "some_file.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "do_not_ignore.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "not_ignore_dir", "not_ignore_file.txt")))

        self.assertFalse(os.path.exists(os.path.join(self.output_dir, "please_ignore.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.output_dir, "ignore_dir", "ignore_file.txt")))
        # fmt: on


if __name__ == "__main__":
    unittest.main()
