import hashlib
import os
import subprocess
import sys
import tempfile
import time
import traceback

from pathspec import PathSpec

VERSION: int = 1


def load_ignore_rules(directory) -> PathSpec:
    if os.path.isfile(os.path.join(directory, ".gitignore")):
        with open(os.path.join(directory, ".gitignore"), "r") as f:
            return PathSpec.from_lines("gitwildmatch", f.readlines())
    else:
        return PathSpec.from_lines("gitwildmatch", [])


def get_non_ignored_files(base_path) -> list[str]:
    spec = load_ignore_rules(base_path)
    files = spec.match_tree_files(base_path, negate=True)
    return list(files)


def calculate_checksum(file_path) -> str:
    checksum = hashlib.sha256(open(file_path, "rb").read()).hexdigest()
    return checksum


def calculate_files_checksum(files: list[str]) -> dict:
    checksums = {}
    for file in files:
        checksums[file] = calculate_checksum(file)
    return checksums


def compress_files(source: str, output: str) -> None:
    try:
        print(f"Compressing '{source}'...")
        temp_archive_path = os.path.join(
            output,
            f"{os.path.basename(source)}_{time.strftime("%Y%m%d%H%M%S%z")}.tmp",
        )

        # On Windows, commands that are too long may cause WinError 206
        # So we use -i@file instead
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            os.chdir(source)  # 7z doesn't support relative paths
            temp_file.write("\n".join(get_non_ignored_files(source)).encode("utf-8"))
            temp_file.close()
            compress_command = [
                "7z",
                "a",
                temp_archive_path,
                "-m0=lzma2",
                "-mx=9",  # compression level
                "-mmt=on",  # multi-threading
                "-ms=on",  # solid archive
                "-i@" + temp_file.name,
            ]
            subprocess.run(compress_command, check=True)

        checksum = calculate_checksum(temp_archive_path)[:8]
        output_archive_path = os.path.join(
            output,
            temp_archive_path.replace(".tmp", f"_{checksum}.7z"),
        )
        os.rename(temp_archive_path, output_archive_path)
        print(f"Folder '{source}' compressed successfully to '{output_archive_path}'.")
    except subprocess.CalledProcessError as e:
        print(f"Error during compression: {e}", file=sys.stderr)
        traceback.print_exc()
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        traceback.print_exc()
    finally:
        if os.path.isfile(temp_archive_path):
            os.remove(temp_archive_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compression script calls 7z cli")
    parser.add_argument("-i", "--input", help="Folder to compress", required=True)
    parser.add_argument("-o", "--output", help="Output directory", default=os.getcwd())
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run")

    print("Script version: {}".format(VERSION))

    args = parser.parse_args()

    if not os.path.isdir(args.input):
        raise ValueError(f"'{args.input}' is not a valid directory.")

    if not os.path.isdir(args.output):
        raise ValueError(f"'{args.output}' is not a valid directory.")

    source_directory = os.path.abspath(args.input)
    output_directory = os.path.abspath(args.output)

    if args.dry_run:
        print("This is a dry run. No compression will be performed.")
        print(f"Folder to compress: {source_directory}")
        print(f"Output directory: {output_directory}")
        print("Getting files to be compress...")
        files = get_non_ignored_files(source_directory)
        print("Files to be compress:")
        for file in files:
            print(file)
        sys.exit(0)

    compress_files(source_directory, output_directory)
