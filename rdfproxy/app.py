"""Simple Flask application to serve RDF data as documents from a graph."""

from http import HTTPStatus
from typing import Any
from typing import Dict
from logging import basicConfig
from logging import DEBUG
from logging import INFO
from logging import error
from logging import warning
from logging import exception
from datetime import UTC
from datetime import datetime
from traceback import format_exc

from flask import Flask
from flask import request
from flask import render_template
from flask import send_file
from flask.wrappers import Response

from flask_cors import CORS as FlaskCORS

from mistune import Markdown
from mistune import HTMLRenderer

from jinja2.exceptions import TemplateNotFound

from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import NotFound
from werkzeug.exceptions import NotAcceptable

from rdflib.term import URIRef
from rdflib.namespace import RDF
from rdflib.namespace import OWL
from rdflib.namespace import SDO

from resources import get_document_data
from utils import uri_to_path
from utils import sort_by_predicate
from utils import remove_file_uris
from utils import get_request_host
from utils import get_request_hostname
from utils import get_request_proto
from templates import find_template
from templates import TEMPLATE_PATH
from constants import ACCEPT_MIMETYPES
from constants import MIMETYPE_FORMATS

# The Flask application, with template clean-ups
app = Flask(import_name=__name__, template_folder=TEMPLATE_PATH)
app.jinja_env.lstrip_blocks = True
app.jinja_env.trim_blocks = True

# Custom filters
app.jinja_env.filters["sort_by_predicate"] = sort_by_predicate

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

# Configure Mistune
html = Markdown(renderer=HTMLRenderer(escape=False, allow_harmful_protocols=False))


@app.get("/")
@app.get("/<path:path>")
def get_document(path: str = "/") -> Response:
    """Return a document-scoped collection of CBDs in the client-preferrec format."""

    # Find the document graph based on original client-facing URI
    document_uri = URIRef(
        value=path, base=f"{get_request_proto()}://{get_request_host()}"
    )
    document_dataset = get_document_data(uri=document_uri)
    document_mimetype: str | None = None

    if not document_dataset:
        raise NotFound()

    available_mimetypes = [*ACCEPT_MIMETYPES]

    # Check if the document is a schema:MediaObject with mimetype
    if (document_uri, RDF.type, SDO.MediaObject) in document_dataset:
        document_mimetype = document_dataset.value(
            subject=document_uri,
            predicate=SDO.encodingFormat,
        )
        available_mimetypes.remove("text/html")
        available_mimetypes.insert(0, document_mimetype)

    mimetype = (
        request.accept_mimetypes.best_match(available_mimetypes)
        if request.accept_mimetypes.provided
        else available_mimetypes[0]
    )

    if not mimetype:
        raise NotAcceptable()

    same_as = document_dataset.value(subject=document_uri, predicate=OWL.sameAs)

    if same_as and isinstance(same_as, URIRef):
        return Response(
            status=HTTPStatus.TEMPORARY_REDIRECT,
            headers={"location": same_as},
        )

    if mimetype == document_mimetype:
        return send_file(
            path_or_file=uri_to_path(
                document_dataset.value(
                    subject=document_uri,
                    predicate=SDO.contentUrl,
                )
            ),
            mimetype=mimetype,
        )

    format_keyword = MIMETYPE_FORMATS[mimetype]

    # Remove the actual file URI before serving the graph
    document_dataset = remove_file_uris(dataset=document_dataset)

    if format_keyword == "html":
        template_name, template_type = find_template(
            uri=document_uri,
            type_uris=document_dataset.objects(
                subject=document_uri,
                predicate=RDF.type,
                unique=True,
            ),
        )
        if template_name:
            return render_template(
                template_name,
                uri=document_uri,
                type=template_type,
                graph=document_dataset,
            )
    else:
        return Response(
            response=document_dataset.serialize(format=format_keyword),
            mimetype=mimetype,
        )

    warning(f"No {format_keyword} template found for {document_uri.n3()}")

    raise NotAcceptable()


@app.context_processor
def handle_context() -> Dict[str, Any]:
    """Add various utility types into the template context."""
    return {
        "year": datetime.now(tz=UTC).year,
        "html": html,
    }


@app.errorhandler(Exception)
def handle_error(exc: Exception) -> Response:
    """Return a representation of a server error."""

    response: str | None = None

    if isinstance(exc, HTTPException):
        status_code = exc.code
    else:
        exception(exc)
        status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value

    if request.accept_mimetypes.accept_html:
        try:
            response = render_template(
                template_name_or_list=[
                    f"{get_request_hostname()}/_{status_code}.html",
                    f"{get_request_hostname()}/_error.html",
                    f"_{status_code}.html",
                    "_error.html",
                ],
                error=format_exc() if app.debug else str(exc),
            )
        except TemplateNotFound as ex:
            error(ex)

    return Response(response=response, status=status_code)
