##########################
# Prepare Edirom Content #
##########################
FROM ghcr.io/korngold-werkausgabe/saxon-cmd:latest

WORKDIR /app
COPY . .

RUN mkdir -p Edirom/content/{critical-report,documents,edition,introduction,sources,structure}

# PRE BUILD FILES #
RUN xquery -q:buildEdiromTkAs.xql -o:./tmp/annots.xml
RUN xquery s:Edirom/nav.xml -q:buildNav.xql -o:./tmp/nav.xml
RUN xquery -q:buildConnectionsByCSV.xql -o:./tmp/conc.xml

# BUILD FILES #
RUN xslt -s:template_edirom-works.xml -q:mergeTkAsinWorks.xsl -o:Edirom/content/structure/edirom-works.xml
RUN xslt -s:template_edirom-file.xml -q:buildEdiromFile.xsl -o:Edirom/content/structure/edirom.xml

# COPY #
RUN mv edirom_source*.xml Edirom/content/sources
RUN mv Edirom/local.properties Edirom/prefs.xml Edirom/content

########################
# Build edirom content #
########################
FROM openjdk:25-jdk-bullseye AS build-content

RUN apt-get update \
    && apt-get install -y --no-install-recommends ant 

RUN git clone -b develop --single-branch --recursive https://github.com/Edirom/Edirom-Edition-Packaging.git

WORKDIR /Edirom-Edition-Packaging
COPY ../Edirom/content .

RUN ant -Duri.edition=/Edirom-Edition-Packaging xar
