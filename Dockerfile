FROM python:alpine

ADD ./rdfdp /opt/rdfdp
ADD ./example /usr/share/rdfdpdata
ADD ./requirements.txt /opt/rdfdp/requirements.txt

WORKDIR /opt/rdfdp

RUN python -m pip install --upgrade pip setuptools
RUN python -m pip install -r requirements.txt
RUN python -m pip install gunicorn>=23.0.0

ENV DATA_PATH=/usr/share/rdfdpdata/data
ENV QUERIES_PATH=/usr/share/rdfdpdata/queries
ENV TEMPLATE_PATH=/usr/share/rdfdpdata/templates

RUN adduser --no-create-home --disabled-password --uid 1000 --shell /bin/sh rdfdp

USER rdfdp

ENTRYPOINT [ "gunicorn", "app:app" ]
