"""Helper utilities."""

from os import getenv
from os.path import splitext
from typing import Iterable
from pathlib import Path
from hashlib import sha256
from urllib.parse import unquote
from urllib.parse import urlparse

from rdflib.term import URIRef

CHUNK_SIZE = 64 * 1024


def get_file_sha256sum(path: Path) -> str:
    """Generates the SHA256 checksum for a file."""

    path_sha256 = sha256(usedforsecurity=False)

    with open(path, "rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)
            if chunk:
                path_sha256.update(chunk)
            else:
                break

    return path_sha256.hexdigest()


def uri_to_path(uri: str) -> Path:
    """Converts a file URI into a file path."""

    parsed_uri = urlparse(unquote(uri))
    assert parsed_uri.scheme == "file", f"Invalid scheme {parsed_uri.scheme}"
    assert parsed_uri.path.startswith("/"), f"Invalid path {parsed_uri.path}"

    return Path(parsed_uri.path).resolve(strict=True)


def find_files(path: Path, extensions: Iterable[str]) -> Iterable[Path]:
    """Iterates over all files in the specified path, with the provided extensions."""

    queue = [path]

    while queue:
        path = queue.pop(0)
        if path.is_dir():
            queue.extend(path.iterdir())
        elif splitext(path)[1] in extensions:
            yield path


def env_to_path(key: str, default: str | None = None) -> Path:
    """Attempts to resolve an environment variable into a path."""

    value = getenv(key) or default

    assert value, f"Undefined environment variable {key}"

    return Path(value).resolve(strict=True)


def partition_to_fragment(dataset_uri: URIRef, partition_uri: URIRef) -> URIRef:
    """Converts partition URIs from RDFLib's VoID generator into fragments."""

    partition_name = partition_uri.removeprefix(dataset_uri).encode("utf-8")
    partition_hash = sha256(partition_name, usedforsecurity=False).hexdigest()
    partition_fragment = URIRef(value=f"#{partition_hash}", base=dataset_uri)

    return partition_fragment
