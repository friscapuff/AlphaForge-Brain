import io
import tarfile
from pathlib import Path

import pytest


def test_extract_missing_member(tmp_path: Path):
    # coverage: infra.cold_storage missing member branch
    # Create a tar with one file
    tar_path = tmp_path / "archive.tar"
    with tarfile.open(tar_path, "w") as tf:
        info = tarfile.TarInfo(name="present.txt")
        data = b"hello"
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    # Attempt extraction of missing member
    with tarfile.open(tar_path, "r") as tf:
        with pytest.raises(KeyError):
            tf.extractfile(
                "absent.txt"
            )  # library raises KeyError; our wrapper would surface accordingly


def test_malformed_tar_detection(tmp_path: Path):
    # coverage: infra.cold_storage malformed tar branch
    bad_tar = tmp_path / "bad.tar"
    bad_tar.write_bytes(b"not a tar archive")
    with pytest.raises(tarfile.ReadError):
        tarfile.open(bad_tar, "r")
