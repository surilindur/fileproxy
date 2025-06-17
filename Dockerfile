FROM alpine:edge

RUN apk --repository=http://dl-cdn.alpinelinux.org/alpine/edge/testing/ add pypy3

RUN pypy3 -m ensurepip
RUN pypy3 -m pip install --upgrade pip setuptools

ADD ./rdfdp /opt/rdfdp
ADD ./example /usr/share/rdfdpdata
ADD ./requirements.txt /opt/rdfdp/requirements.txt

WORKDIR /opt/rdfdp

RUN pypy3 -m pip install -r requirements.txt
RUN pypy3 -m pip install gunicorn[gevent]>=23.0.0

ENV DATA_PATH=/usr/share/rdfdpdata/data
ENV QUERIES_PATH=/usr/share/rdfdpdata/queries
ENV TEMPLATE_PATH=/usr/share/rdfdpdata/templates

RUN adduser --no-create-home --disabled-password --uid 1000 --shell /bin/sh rdfdp

USER rdfdp

EXPOSE 8000

ENTRYPOINT [ "pypy3", "-m", "gunicorn", "app:app" ]
