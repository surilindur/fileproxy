<p align="center">
  <img alt="logo" src="./.github/assets/logo.svg" width="64">
</p>

<p align="center">
  <a href="https://github.com/surilindur/rdfdp/actions/workflows/ci.yml"><img alt="CI" src=https://github.com/surilindur/rdfdp/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/%3C%2F%3E-Python-%233776ab.svg"></a>
  <a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/Code%20Style-black-000000.svg"></a>
  <a href="https://opensource.org/licenses/MIT"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-%23750014.svg"></a>
</p>

Experimental simple Flask application to serve resources from local documents with content negotiation.
Everything is declared in RDF, including static assets, to enable content negotiation over all resources.

Upon first request, the application loads all RDF documents from the specified path on disk into an in-memory store,
and fills in the remaining metadata for static assets, such as checksums and modification date,
as well as executes all queries sorted by their names on this in-memory dataset.
The application also generates a VoID description for each distinct hostname in the data, to treat them as datasets.

For each response, the application attempts to find a corresponding resource from the in-memory store.
When a resource is found, content negotiation is performed over this resource.
For static assets, the native media type is preferred over the RDF metadata representations.
For RDF resources, Turtle serialization is preferred in absence of accepted types.

## Dependencies

* Python
* [RDFLib](https://github.com/RDFLib/rdflib)
* [Flask](https://github.com/pallets/flask)
* [Flask-CORS](https://github.com/corydolphin/flask-cors)
* [Mistune](https://github.com/lepture/mistune)

## Usage

The application can be configured using environment variables:

* `DATA_PATH`: The RDF data directory.
* `QUERIES_PATH`: The queries directory.
* `TEMPLATE_PATH`: The path to the templates directory.

The following HTTP proxy headers will be taken into consideration when identifying actual resource URIs:

* `X-Forwarded-For`: Substituted for the host value when provided.
* `X-Forwarded-Proto`: Substituted for the protocol value when provided.

Further configuration is possible for Flask and Flask-CORS via [environment variables](https://flask.palletsprojects.com/en/stable/api/#flask.Config.from_prefixed_env).
For example, to configure [Flask-CORS](https://flask-cors.readthedocs.io/en/latest/configuration.html):

* `FLASK_CORS_ALWAYS_SEND=false` to not force send CORS headers when not requested.
* `FLASK_CORS_MAX_AGE=3600` to set `Access-Control-Max-Age` to 3600 seconds.
* `FLASK_CORS_METHODS='[ "GET", "HEAD", "OPTIONS" ]'` to only allow `GET` and `HEAD` requests.
* `FLASK_CORS_ORIGINS='*'` to allow any `Origin`.
* `FLASK_CORS_SUPPORTS_CREDENTIALS=true` to avoid CORS errors when credentials are provided.

Or to set some options for [Flask](https://flask.palletsprojects.com/en/stable/config/):

* `FLASK_USE_X_SENDFILE=true` to use `X-Sendfile` header with a proxy server.

## Resources

The resources are defined in RDF, with static assets declared as `schema:MediaObject` with their on-disk file URIs.
Only the resources defined in RDF are served by the proxy, under their defined URIs.
The URI of the resource definitions must match the public exposed URIs of the application.
For examples, see the definitions in the [example](./example/) directory.

## Templates

The template is selected based on the types of the document URI.
For example, if the document URI is declared as having `rdf:type` of `schema:BlogPosting`, then `BlogPosting.html` is selected as the template.
The fallback default template name is `_default.html`.
The fallback error template name is `_error.html`, and HTTP status code errors use templates such as `_500.html`.

The following variables are made available to the templates:

* Current year as `current_year`
* Current document graph as `document_graph`
* Current document URI as `document_uri`
* Current error code as `error_code` if available, error title as `error_title`, and error message as `error_message`
* Current type name used to select template as `template_type` unless using the default template

The following filters are available to the templates:

* Markdown-to-HTML conversion function as `markdown_to_html`
* Predicate value-based subject sorting function as `sort_by_predicate`

## Issues

Please feel free to report any issues on the GitHub issue tracker.

## License

This code is copyrighted and released under the [MIT license](http://opensource.org/licenses/MIT).
