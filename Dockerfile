FROM python:alpine

ADD rdfproxy /opt/rdfproxy

ADD example/data /opt/rdfproxy/data
ADD example/queries /opt/rdfproxy/queries
ADD example/templates /opt/rdfproxy/templates

ADD requirements.txt /opt/rdfproxy/requirements.txt

WORKDIR /opt/rdfproxy

RUN python -m pip install --upgrade pip setuptools
RUN python -m pip install -r requirements.txt
RUN python -m pip install gunicorn>=23.0.0

RUN adduser --no-create-home --disabled-password --uid 1000 --shell /bin/sh rdfproxy

USER rdfproxy

ENTRYPOINT [ "gunicorn", "app:app" ]
