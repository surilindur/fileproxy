FROM python:alpine

ADD fileproxy /opt/fileproxy

ADD example/data /opt/fileproxy/data
ADD example/queries /opt/fileproxy/queries
ADD example/templates /opt/fileproxy/templates

ADD requirements.txt /opt/fileproxy/requirements.txt

WORKDIR /opt/fileproxy

RUN python -m pip install --upgrade pip setuptools
RUN python -m pip install -r requirements.txt
RUN python -m pip install gunicorn>=23.0.0

RUN adduser --no-create-home --disabled-password --uid 1000 --shell /bin/sh fileproxy

USER fileproxy

ENTRYPOINT [ "gunicorn", "app:app" ]
