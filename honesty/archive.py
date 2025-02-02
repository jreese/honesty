import hashlib
import os.path
from pathlib import Path
from typing import Dict, List, Tuple

import arlib

ZIP_EXTENSIONS = (".zip", ".egg", ".whl")


def extract_and_get_names(
    archive_filename: Path, strip_top_level: bool = False
) -> Tuple[str, List[Tuple[str, str]]]:
    cache_path = os.path.expanduser(
        os.environ.get("HONESTY_EXTDIR", "~/.cache/honesty/ext")
    )
    archive_root = os.path.join(cache_path, archive_filename.name)
    if not os.path.exists(archive_root + ".done"):
        engine = (
            arlib.ZipArchive if str(archive_filename).endswith(ZIP_EXTENSIONS) else None
        )
        with arlib.open(archive_filename, "r", engine=engine) as archive:
            archive.extract(path=archive_root)

    with open(archive_root + ".done", "w"):
        pass

    # relpath, srcpath
    names: List[Tuple[str, str]] = []
    # TODO figure out the right level of parallelism and/or use cfv
    for dirpath, dirnames, filenames in os.walk(archive_root):
        for name in filenames:
            if not name.endswith(".py"):
                continue  #  skip for now

            relname = os.path.join(dirpath[len(archive_root) + 1 :], name)

            srckey = relname
            # To do this right, we need to read setup.py to know how it gets
            # mapped, but this is an 80% solution.
            if strip_top_level:
                srckey = srckey.split("/", 1)[-1]
            if srckey.startswith("src/"):
                srckey = srckey[4:]

            names.append((relname, srckey))

    return (archive_root, names)


# [path] = sha
def archive_hashes(
    archive_filename: Path, strip_top_level: bool = False
) -> Dict[str, str]:
    d: Dict[str, str] = {}
    archive_root, names = extract_and_get_names(archive_filename, strip_top_level)

    for relname, srcname in names:
        with open(os.path.join(archive_root, relname), "rb") as buf:
            data = buf.read().replace(b"\r\n", b"\n")

        sha = hashlib.sha1(data).hexdigest()
        d[srcname] = sha
    return d
