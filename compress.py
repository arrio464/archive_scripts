import hashlib
import os
import subprocess
import sys
import tempfile
import time
import traceback

from pathspec import PathSpec


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
    return checksum[:8]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compression script calls 7z cli")
    parser.add_argument("-i", "--input", help="Directory to compress", required=True)
    parser.add_argument("-o", "--output", help="Output directory", default=os.getcwd())
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run")

    args = parser.parse_args()

    if not os.path.isdir(args.input):
        raise ValueError(f"'{args.input}' is not a valid directory.")

    if not os.path.isdir(args.output):
        raise ValueError(f"'{args.output}' is not a valid directory.")

    input_dir = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)

    if args.dry_run:
        print("This is a dry run. No compression will be performed.")
        print(f"Input directory: {input_dir}")
        print(f"Output directory: {output_dir}")
        print("Files to be compressed:")
        files = get_non_ignored_files(input_dir)
        for file in files:
            print(file)
        sys.exit(0)

    try:
        print(f"Compressing '{input_dir}'...")
        temp_archive_path = os.path.join(
            os.path.abspath(args.output),
            f"{os.path.basename(input_dir)}_{time.strftime("%Y%m%d%H%M%S%z")}.tmp",
        )

        # On Windows, commands that are too long may cause WinError 206
        # So we use -i@file instead
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            os.chdir(input_dir)  # 7z doesn't support relative paths
            temp_file.write("\n".join(get_non_ignored_files(input_dir)).encode("utf-8"))
            temp_file.close()
            compress_command = [
                "7z",
                "a",
                temp_archive_path,
                "-m0=lzma2",
                "-mx=7",  # compression level
                "-mmt=on",  # multi-threading
                "-ms=on",  # solid archive
                "-i@" + temp_file.name,
            ]
            subprocess.run(compress_command, check=True)

        checksum = calculate_checksum(temp_archive_path)
        output_archive_path = os.path.join(
            os.path.abspath(args.output),
            temp_archive_path.replace(".tmp", f"_{checksum}.7z"),
        )
        os.rename(temp_archive_path, output_archive_path)
        print(
            f"Folder '{input_dir}' compressed successfully to '{output_archive_path}'."
        )
    except subprocess.CalledProcessError as e:
        print(f"Error during compression: {e}", file=sys.stderr)
        traceback.print_exc()
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        traceback.print_exc()
    finally:
        if os.path.isfile(temp_archive_path):
            os.remove(temp_archive_path)
