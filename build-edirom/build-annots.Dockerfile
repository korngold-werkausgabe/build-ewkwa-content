FROM ghcr.io/korngold-werkausgabe/saxon-cmd:latest

WORKDIR /app
COPY build-edirom/buildEdiromTkA-local.xql .
COPY build-edirom/tka_fullScore_03.xml .

RUN xquery -s:tka_fullScore_03.xml -q:buildEdiromTkA-local.xql -o:annots.xml

RUN cat annots.xml