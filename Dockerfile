FROM python:3.8-alpine

RUN apk add --upgrade  \
    build-base \
    libffi-dev \
    openssl-dev \
    mariadb-dev \
    libxml2-dev \
    libxslt-dev \
    py3-psycopg2 \
    zlib-dev \
    jpeg-dev \
    gettext \
    nodejs \
    npm \
    libsass \
    rust \
    cargo \
    git \
    zip \
    unzip \
    nano \
    vim \
    wget \
    curl \
    tar \
    bash

ENV LIBRARY_PATH=/lib:/usr/lib
ENV PYTHONUNBUFFERED 1

RUN wget -q https://github.com/fgrehm/docker-phantomjs2/releases/download/v2.0.0-20150722/dockerized-phantomjs.tar.gz && \
    tar -xzf dockerized-phantomjs.tar.gz -C / && \
    rm -rf dockerized-phantomjs.tar.gz && \
    chmod a+x /usr/local/bin/phantomjs

RUN mkdir -p /app
WORKDIR /app

RUN mkdir -p pdfcache/

RUN pip install --upgrade pip setuptools wheel && \
    pip install gunicorn && \
    pip install gunicorn[gevent] && \
    pip install gunicorn[gthread]

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY package.json .
RUN npm install .

COPY . .

RUN git clone https://github.com/metucclub/docker-scripts && \
    mv docker-scripts/*.sh . && \
    rm -rf docker-scripts && \
    mkdir -p ./db && \
    mkdir -p ./pdfcache

RUN chmod a+x backup-data.sh restore-data.sh docker-wait-for-it.sh
