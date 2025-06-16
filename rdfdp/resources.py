"""Utility functions for accessing the application data."""

from os import stat
from typing import Dict
from pathlib import Path
from logging import debug
from logging import info
from logging import warning
from datetime import datetime
from datetime import UTC
from mimetypes import guess_file_type
from mimetypes import add_type
from functools import cache
from urllib.parse import urljoin

from rdflib.void import generateVoID
from rdflib.term import URIRef
from rdflib.term import Literal
from rdflib.graph import Graph
from rdflib.namespace import RDF
from rdflib.namespace import SDO
from rdflib.namespace import XSD
from rdflib.namespace import VOID

from constants import CUSTOM_PREFIXES
from constants import CUSTOM_MIMETYPES
from constants import FILE_URI_PREFIX
from constants import RDF_FILE_EXTENSIONS
from constants import XSD_DATETIME_FORMAT
from constants import SPARQL_FILE_EXTENSIONS
from constants import CONTENT_EMBED_PREDICATES
from utils import partition_to_fragment
from utils import get_file_sha256sum
from utils import uri_to_path
from utils import env_to_path
from utils import find_files


# Add custom mimetypes, or missing ones
for mimetype, extension in CUSTOM_MIMETYPES.items():
    add_type(mimetype, extension, strict=False)


def parse_rdf_file(path: Path) -> Graph:
    """Loads the specified file as RDF into the graph."""

    graph = Graph(identifier=path.as_posix())
    graph.parse(source=path)

    for s, p, o in graph:
        if isinstance(o, URIRef) and o.startswith(FILE_URI_PREFIX):
            o_tail = o.removeprefix(FILE_URI_PREFIX)
            o_path = path.parent.joinpath(o_tail).resolve(strict=True)
            if p in CONTENT_EMBED_PREDICATES:
                warning(f"Loading content from {o_path}")
                with open(o_path, "r", encoding="utf-8") as o_file:
                    graph.set((s, p, Literal(o_file.read())))
            else:
                graph.remove((s, p, o))
                graph.add((s, p, URIRef(o_path.as_uri())))

    for s in graph.subjects(predicate=RDF.type, object=SDO.MediaObject):
        s_uri = next(
            (
                u
                for u in graph.objects(subject=s, predicate=SDO.contentUrl)
                if isinstance(u, URIRef) and u.startswith(FILE_URI_PREFIX)
            ),
            None,
        )

        if not s_uri:
            warning(f"Skip metadata extraction for {s.n3()}")
            continue

        s_path = uri_to_path(s_uri)

        # Add name
        graph.set((s, SDO.name, Literal(s_path.name)))

        # Add mimetype
        s_type = guess_file_type(path=s_path, strict=False)[0]
        graph.set((s, SDO.encodingFormat, Literal(s_type)))

        # Add SHA256 checksum
        graph.set((s, SDO.sha256, Literal(get_file_sha256sum(path=s_path))))

        # Add file size in bytes
        s_stat = stat(path=s_path)
        graph.set((s, SDO.size, Literal(str(s_stat.st_size), datatype=XSD.integer)))

        # Add creation and edit dates
        for ts, predicate in (
            (s_stat.st_ctime, SDO.dateCreated),
            (s_stat.st_mtime, SDO.dateModified),
        ):
            ts_datetime = datetime.fromtimestamp(timestamp=ts, tz=UTC)
            graph.set(
                (
                    s,
                    predicate,
                    Literal(
                        ts_datetime.strftime(XSD_DATETIME_FORMAT),
                        datatype=XSD.dateTime,
                    ),
                )
            )

    debug(f"Loaded {len(graph)} triples from {path}")

    return graph


@cache
def get_dataset() -> Graph:
    """Loads all data from the specified path as an RDF graph."""

    data_path = env_to_path("DATA_PATH", "data")
    queries_path = env_to_path("QUERIES_PATH", "queries")

    graph = Graph(identifier=data_path.as_posix())

    for path in find_files(path=data_path, extensions=RDF_FILE_EXTENSIONS):
        info(f"Loading {path}")
        graph += parse_rdf_file(path=path)

    for path in find_files(path=queries_path, extensions=SPARQL_FILE_EXTENSIONS):
        info(f"Applying {path}")
        with open(path, "r", encoding="utf-8") as query_file:
            graph.update(query_file.read())

    info("Grouping into datasets for VoID generation")

    datasets_for_void: Dict[URIRef, Graph] = {}
    non_uri_subjects = 0

    for s, p, o in graph:
        if isinstance(s, URIRef):
            dataset_uri = URIRef(urljoin(base=s, url="/", allow_fragments=False))
            if dataset_uri not in datasets_for_void:
                datasets_for_void[dataset_uri] = Graph(identifier=dataset_uri)
            graph.cbd(resource=s, target_graph=datasets_for_void[dataset_uri])
        else:
            non_uri_subjects += 1

    if non_uri_subjects:
        warning(f"Detected {non_uri_subjects} non-URI resources")

    for dataset_uri, dataset_graph in datasets_for_void.items():
        info(f"Generating VoID description for {dataset_uri.n3()}")
        dataset_void = generateVoID(
            g=dataset_graph,
            dataset=dataset_uri,
            distinctForPartitions=True,
        )[0]

        # Convert underscore identifiers to fragments on the dataset URI
        partition_prefix = f"{dataset_uri}_"
        for s, p, o in dataset_void:
            if isinstance(s, URIRef) and s.startswith(partition_prefix):
                s = partition_to_fragment(dataset_uri=dataset_uri, partition_uri=s)
            if isinstance(o, URIRef) and o.startswith(partition_prefix):
                o = partition_to_fragment(dataset_uri=dataset_uri, partition_uri=o)
            graph.add((s, p, o))

        # Add void:uriSpace
        graph.add((dataset_uri, VOID.uriSpace, Literal(dataset_uri)))

    info(f"Loaded {len(graph)} triples")

    return graph


@cache
def get_document_data(app_dataset: Graph, uri: URIRef) -> Graph:
    """Collect the resources for a document from the dataset."""

    document_graph = Graph(identifier=uri)

    if app_dataset:
        # Collect the document URI itself, and all associated bnodes
        app_dataset.cbd(resource=uri, target_graph=document_graph)

        # Collect all fragments that belong in the document URI, and their bnodes
        uri_fragment_prefix = f"{uri}#"
        for s in app_dataset.subjects(unique=True):
            if isinstance(s, URIRef) and s.startswith(uri_fragment_prefix):
                app_dataset.cbd(resource=s, target_graph=document_graph)

    # Bind additional namespaces
    for prefix, namespace_uri in CUSTOM_PREFIXES.items():
        document_graph.namespace_manager.bind(prefix=prefix, namespace=namespace_uri)

    return document_graph
