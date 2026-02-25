##########################
# Prepare edirom content #
##########################
FROM python:3.11-slim as prepare-content

RUN apt-get update && apt-get install -y \
    saxon \
    xquery \
    basex \
    && rm -rf /var/lib/apt/lists/*

COPY . /app
WORKDIR /app

RUN python3 prepare-content.py

########################
# Build edirom content #
########################
FROM eclipse-temurin:21 AS build-content

RUN apt-get update \
    && apt-get install -y --no-install-recommends ant git

RUN git clone -b develop --single-branch --recursive https://github.com/Edirom/Edirom-Edition-Packaging.git

WORKDIR /Edirom-Edition-Packaging
COPY --from=prepare-content /app/Edirom/content .

RUN ant -Duri.edition=/Edirom-Edition-Packaging xar

########################
# Final output stage   #
########################
FROM alpine:latest AS final
COPY --from=prepare-content /app /home/debug-prepare-content
COPY --from=build-content /Edirom-Edition-Packaging/dist/*.xar /output/