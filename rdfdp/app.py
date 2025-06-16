"""Simple Flask application to serve RDF data as documents from a graph."""

from http import HTTPStatus
from typing import Any
from typing import Dict
from logging import basicConfig
from logging import DEBUG
from logging import INFO
from logging import debug
from logging import error
from logging import warning
from logging import exception
from datetime import datetime
from traceback import format_exc

from flask import Flask
from flask import request
from flask import render_template
from flask import send_file
from flask.wrappers import Response

from flask_cors import CORS as FlaskCORS

from jinja2.exceptions import TemplateNotFound

from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import NotFound
from werkzeug.exceptions import NotAcceptable

from rdflib.term import URIRef
from rdflib.term import Literal
from rdflib.namespace import RDF
from rdflib.namespace import OWL
from rdflib.namespace import SDO

from resources import get_document_datasets
from utils import uri_to_path
from utils import sort_by_predicate
from utils import remove_file_uris
from utils import markdown_to_html
from utils import get_request_host
from utils import get_request_hostname
from utils import get_request_proto
from templates import load_templates
from templates import find_template
from templates import TEMPLATE_PATH
from constants import UTC
from constants import ACCEPT_MIMETYPES
from constants import MIMETYPE_FORMATS

# The Flask application, with template clean-ups
app = Flask(import_name=__name__, template_folder=TEMPLATE_PATH)
app.jinja_env.lstrip_blocks = True
app.jinja_env.trim_blocks = True

# Custom filters
app.jinja_env.filters["sort_by_predicate"] = sort_by_predicate
app.jinja_env.filters["markdown_to_html"] = markdown_to_html

# Load configuration from environment variables if available
app.config.from_prefixed_env()

# Configure logging
basicConfig(
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
    level=DEBUG if app.debug else INFO,
)

# Setup Flask-CORS
cors = FlaskCORS(app=app)

# Collect the application dataset into cache at the beginning
app_datasets = get_document_datasets()
app_templates = load_templates()


@app.get("/")
@app.get("/<path:path>")
def get_document(path: str = "/") -> Response:
    """Return a document-scoped collection of CBDs in the client-preferrec format."""

    # Find the document graph based on original client-facing URI
    document_uri = URIRef(
        value=path, base=f"{get_request_proto()}://{get_request_host()}"
    )

    if document_uri not in app_datasets:
        raise NotFound()

    document_graph = app_datasets[document_uri]
    document_mimetype: str | None = None

    available_mimetypes = ACCEPT_MIMETYPES

    # Check if the document is a schema:MediaObject with mimetype
    if (document_uri, RDF.type, SDO.MediaObject) in document_graph:
        document_encoding_format = document_graph.value(
            subject=document_uri,
            predicate=SDO.encodingFormat,
        )
        assert isinstance(
            document_encoding_format, Literal
        ), f"Missing schema:encodingFormat on {document_uri.n3()}"
        document_mimetype = document_encoding_format
        available_mimetypes = tuple(
            (document_mimetype, *(m for m in ACCEPT_MIMETYPES if m != "text/html"))
        )

    mimetype = (
        request.accept_mimetypes.best_match(available_mimetypes)
        if request.accept_mimetypes.provided
        else available_mimetypes[0]
    )

    if not mimetype:
        raise NotAcceptable()

    same_as = document_graph.value(subject=document_uri, predicate=OWL.sameAs)

    if same_as and isinstance(same_as, URIRef):
        return Response(
            status=HTTPStatus.TEMPORARY_REDIRECT,
            headers={"location": same_as},
        )

    if mimetype == document_mimetype:
        document_file_uri = document_graph.value(
            subject=document_uri,
            predicate=SDO.contentUrl,
        )
        assert isinstance(
            document_file_uri, URIRef
        ), f"Missing schema:contentUrl on {document_uri.n3()}"

        document_file_path = uri_to_path(document_file_uri).as_posix()
        debug(f"Serving static document from {document_file_path}")

        # Attempt to use X-Accel-Redirect if enables for nginx
        if app.config.get("USE_X_ACCEL_REDIRECT") in ("true", "True", True, 1, "1"):
            return Response(
                status=HTTPStatus.OK,
                headers={"X-Accel-Redirect": document_file_path},
                mimetype=mimetype,
            )

        # Fall back to Flask's X-SendFile support
        return send_file(path_or_file=document_file_path, mimetype=mimetype, etag=True)

    format_keyword = MIMETYPE_FORMATS[mimetype]

    # Remove the actual file URI before serving the graph
    document_graph = remove_file_uris(graph=document_graph)

    # Helps identify content negotiation issues
    debug(f"Serving {document_uri.n3()} as {mimetype}")

    if format_keyword == "html":
        document_type_uris = (
            u
            for u in document_graph.objects(
                subject=document_uri,
                predicate=RDF.type,
                unique=True,
            )
            if isinstance(u, URIRef)
        )
        template_name, template_type = find_template(
            uri=document_uri,
            type_uris=document_type_uris,
            app_templates=app_templates,
        )
        if template_name:
            html_string = render_template(
                app_debug=app.debug,
                template_name_or_list=template_name,
                template_type=template_type,
                document_uri=document_uri,
                document_graph=document_graph,
            )
            return Response(response=html_string, mimetype=mimetype)
    else:
        return Response(
            response=document_graph.serialize(format=format_keyword),
            mimetype=mimetype,
        )

    warning(f"No {format_keyword} template found for {document_uri.n3()}")

    raise NotAcceptable()


@app.context_processor
def handle_context() -> Dict[str, Any]:
    """Add various utility types into the template context."""
    return {"current_year": datetime.now(tz=UTC).year}


@app.errorhandler(Exception)
def handle_error(exc: Exception) -> Response:
    """Return a representation of a server error."""

    response: str | None = None

    if isinstance(exc, HTTPException):
        status_code = exc.code
        status_name = exc.name
        status_description = exc.description
    else:
        exception(exc)
        status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
        status_name = HTTPStatus.INTERNAL_SERVER_ERROR.phrase
        status_description = HTTPStatus.INTERNAL_SERVER_ERROR.description

    if (
        status_code != HTTPStatus.NOT_ACCEPTABLE.value
        and request.accept_mimetypes.provided
        and "text/html" in request.accept_mimetypes
    ):
        try:
            response = render_template(
                template_name_or_list=[
                    f"{get_request_hostname()}/_{status_code}.html",
                    f"{get_request_hostname()}/_error.html",
                    f"_{status_code}.html",
                    "_error.html",
                ],
                app_debug=app.debug,
                error_code=status_code,
                error_title=status_name,
                error_description=status_description,
                error_message=format_exc() if app.debug else str(exc),
            )
        except TemplateNotFound as ex:
            error(ex)

    return Response(response=response, status=status_code)
