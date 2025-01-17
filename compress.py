import hashlib
import io
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

from pathspec import PathSpec

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

MAJOR_VERSION = 0
MINOR_VERSION = 1
PATCH_VERSION = 0
VERSION = f"{MAJOR_VERSION}.{MINOR_VERSION}.{PATCH_VERSION}"


def load_gitignore_rules(ignore_file: Path) -> PathSpec:
    """Load ignore rules from a single .gitignore file."""
    if not ignore_file.exists():
        return PathSpec.from_lines("gitwildmatch", [])

    with ignore_file.open("r") as f:
        rules = [line.strip() for line in f.readlines() if line.strip()]
    return PathSpec.from_lines("gitwildmatch", rules)


def get_non_ignored_files(base_path: Path, ignore_filename: str) -> list[str]:
    """Get non-ignored files by processing each subdirectory with its own ignore rules."""
    # Build a mapping of directory -> ignore rules
    dir_to_spec = {}
    for ignore_file in base_path.rglob(ignore_filename):
        dir_to_spec[ignore_file.parent] = load_gitignore_rules(ignore_file)

    # Recursive traversal with merged ignore rules
    def is_ignored(path: Path) -> bool:
        # Traverse up the directory tree and check each applicable `.gitignore`
        for parent in path.parents:
            if parent in dir_to_spec:
                rel_path = path.relative_to(parent)
                if dir_to_spec[parent].match_file(str(rel_path)):
                    return True
        return False

    # Collect non-ignored files
    all_files = []
    for path in base_path.rglob("*"):
        if path.is_file() and not is_ignored(path):
            all_files.append(str(path.relative_to(base_path)))
    return all_files


def calculate_checksum(file_path: Path) -> str:
    checksum = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return checksum


def calculate_files_checksum(files: list[Path]) -> dict:
    checksums = {}
    for file in files:
        checksums[file] = calculate_checksum(file)
    return checksums


def compress_files(source: Path, output: Path, ignore_filename: str) -> Path:
    try:
        print(f"Compressing '{source}'...")
        timestamp = time.strftime("%Y%m%d%H%M%S%z")
        source_name = source.name
        temp_archive = output / f"{source_name}_{timestamp}.tmp"

        # On Windows, commands that are too long may cause WinError 206
        # So we use -i@file instead
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(
                "\n".join(get_non_ignored_files(source, ignore_filename)).encode(
                    "utf-8"
                )
            )
            temp_file.close()
            compress_command = [
                "7z" if os.name == "nt" else "7zz",
                "a",
                str(temp_archive),
                "-m0=lzma2",
                "-mx=9",  # compression level
                "-mmt=on",  # multi-threading
                "-ms=on",  # solid archive
                "-i@" + temp_file.name,
            ]
            subprocess.run(compress_command, check=True, cwd=str(source))

        checksum = calculate_checksum(temp_archive)[:8]
        output_name = str(temp_archive.name).replace(".tmp", f"_{checksum}.7z")
        output_archive = output / output_name
        temp_archive.rename(output_archive)
        print(f"Folder '{source}' compressed successfully to '{output_archive}'.")
        return output_archive
    except subprocess.CalledProcessError as e:
        print(f"Error during compression: {e}", file=sys.stderr)
        traceback.print_exc()
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        traceback.print_exc()
    finally:
        if temp_archive.exists():
            temp_archive.unlink()


if __name__ == "__main__":
    import argparse

    # fmt: off
    parser = argparse.ArgumentParser(description="Compression script calls 7z cli")
    parser.add_argument("-i", "--input", help="folder to compress", required=True)
    parser.add_argument("-o", "--output", help="output directory", default=os.getcwd())
    parser.add_argument("--alias", help=".gitignore file alias, default is .7zignore", default=".7zignore")
    parser.add_argument("--dry-run", action="store_true", help="perform a dry run")
    parser.add_argument("-v", "--version", version=f"%(prog)s {VERSION}", action="version")
    # fmt: on
    args = parser.parse_args()

    input = Path(args.input)
    output = Path(args.output)

    if not input.is_dir():
        raise ValueError(f"'{input}' is not a valid directory.")

    if not output.is_dir():
        raise ValueError(f"'{output}' is not a valid directory.")

    source_directory = input.resolve()
    output_directory = output.resolve()
    ignore_filename = args.alias

    if args.dry_run:
        print("This is a dry run. No compression will be performed.")
        print(f"Folder to compress: {source_directory}")
        print(f"Output directory: {output_directory}")
        print("Getting files to be compress...")
        files = get_non_ignored_files(source_directory, ignore_filename)
        print("Files to be compress:")
        for file in files:
            print(file)
        sys.exit(0)

    compress_files(source_directory, output_directory, ignore_filename)
