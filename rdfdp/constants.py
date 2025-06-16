"""Constant values used within the application."""

from typing import Set
from typing import Dict
from typing import Sequence
from datetime import timedelta
from datetime import timezone
from collections import OrderedDict

from rdflib.term import URIRef
from rdflib.namespace import SDO

# Workaround for older Python versions
UTC = timezone(offset=timedelta(), name="UTC")

# The prefix of file URIs
FILE_URI_PREFIX = "file://"

# The mimetypes need to be ordered for content negotiation purposes,
# and mapped to format keywords for RDFLib serialization
MIMETYPE_FORMATS: Dict[str, str] = OrderedDict(
    (
        ("text/turtle", "turtle"),
        ("text/plain", "turtle"),
        ("text/html", "html"),
        ("text/n3", "n3"),
        # ("application/hext", "hext"),
        ("application/ld+json", "json-ld"),
        # ("application/n-quads", "nquads"),
        ("application/n-triples", "nt11"),
        ("application/rdf+xml", "pretty-xml"),
        # ("application/trig", "trig"),
        # ("application/trix", "trix"),
    )
)

# Accepted mimetypes in preferential order
ACCEPT_MIMETYPES: Sequence[str] = tuple(MIMETYPE_FORMATS.keys())

# Additional mimetypes used to identify content types of files based on extension
ADDITIONAL_MIMETYPES: Dict[str, str] = {
    ".ttl": "text/turtle",
    ".nt": "application/n-triples",
    ".nq": "application/n-quads",
    ".jsonld": "application/ld+json",
    ".rdf": "application/rdf+xml",
    ".n3": "text/n3",
    ".hext": "application/hext",
    ".trig": "application/trig",
    ".trix": "application/trix",
}

# Convenient set of RDF file extensions only
RDF_FILE_EXTENSIONS: Set[str] = set(ADDITIONAL_MIMETYPES.keys())

# List of SPARQL file extensions
SPARQL_FILE_EXTENSIONS: Set[str] = set((".rq", ".sparql"))

# Set of predicates to load object data directly into from a local file
CONTENT_EMBED_PREDICATES: Set[URIRef] = set((SDO.articleBody, SDO.text))

# The date format used for xsd:dateTime
XSD_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Custom namespace prefixes that are not included in RDFLib by default
CUSTOM_PREFIXES: Dict[str, str] = {
    "vcard": "http://www.w3.org/2006/vcard/ns#",
    "cv": "http://rdfs.org/resume-rdf/cv.rdfs#",
    "pim": "http://www.w3.org/ns/pim/space#",
    "ldp": "http://www.w3.org/ns/ldp#",
    "solid": "http://www.w3.org/ns/solid/terms#",
    "sd": "http://www.w3.org/ns/sparql-service-description#",
}

# Custom mimetypes that are missing for some reason
CUSTOM_MIMETYPES: Dict[str, str] = {
    "image/avif": ".avif",
    "image/webp": ".webp",
    "application/x-bibtex": ".bib",
    "font/woff2": ".woff2",
}
