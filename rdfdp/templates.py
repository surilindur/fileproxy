"""Utiliies for templates."""

from typing import Set
from typing import Tuple
from typing import Dict
from typing import Iterable
from logging import debug
from os.path import splitext
from functools import cache
from urllib.parse import urlparse

from rdflib.term import URIRef

from utils import env_to_path
from utils import find_files

# List of acceptable template extensions
TEMPLATE_EXTENSIONS: Set[str] = set((".html",))

# Path to templates
TEMPLATE_PATH = env_to_path("TEMPLATE_PATH", "templates")

# Defaults
DEFAULT_DOMAIN = "_"
DEFAULT_TEMPLATE = "_default.html"


@cache
def load_templates() -> Dict[str, Dict[str, str]]:
    """Loads all the templates of the application."""

    templates: Dict[str, Dict[str, str]] = {}

    for path in find_files(TEMPLATE_PATH, TEMPLATE_EXTENSIONS):
        path_name = splitext(path.name)[0]
        path_domain = (
            DEFAULT_DOMAIN if path.parent == TEMPLATE_PATH else path.parent.name
        )
        if path_domain not in templates:
            templates[path_domain] = {}
        templates[path_domain][path_name] = path.relative_to(TEMPLATE_PATH).as_posix()

    return templates


def find_template(
    uri: URIRef,
    type_uris: Iterable[URIRef],
) -> Tuple[str | None, str | None]:
    """Attempts to locate the template for a resource with the specified types."""

    parsed_uri = urlparse(uri)
    templates = load_templates()
    domain = parsed_uri.hostname if parsed_uri.hostname in templates else DEFAULT_DOMAIN

    if domain in templates:
        domain_templates = templates[domain]

        for type_uri in type_uris:
            type_uri_parsed = urlparse(type_uri)
            type_name = type_uri_parsed.fragment or type_uri_parsed.path.split("/")[-1]
            if type_name in domain_templates:
                template_path = domain_templates[type_name]
                debug(f"Mapped {uri.n3()} to template {template_path}")
                return template_path, type_name

    return None, None
