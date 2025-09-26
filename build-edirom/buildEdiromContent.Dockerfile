##########################
# Prepare edirom content #
##########################
FROM ghcr.io/korngold-werkausgabe/saxon-cmd:latest AS prepare-content

ARG SCRIPT_PATH=build-content-pipeline/build-edirom
ARG TEMPLATES_PATH=${SCRIPT_PATH}/templates

WORKDIR /app
COPY . .

RUN mkdir -p Edirom/content/{critical-report,documents,edition,introduction,structure}

# PRE BUILD FILES #
RUN xquery -q:${SCRIPT_PATH}/buildEdiromTkAs.xql -o:${SCRIPT_PATH}/tmp/annots.xml
RUN xquery -q:${SCRIPT_PATH}/buildConnectionsByCSV.xql -o:${SCRIPT_PATH}/tmp/conc.xml
RUN xslt -s:Edirom/nav.xml -xsl:${SCRIPT_PATH}/buildNav.xsl -o:${SCRIPT_PATH}/tmp/nav.xml

# BUILD FILES #
RUN xslt -s:${TEMPLATES_PATH}/template_edirom-works.xml -xsl:${SCRIPT_PATH}/mergeTkAsinWorks.xsl -o:Edirom/content/structure/edirom-works.xml
RUN xslt -s:${TEMPLATES_PATH}/template_edirom-file.xml -xsl:${SCRIPT_PATH}/buildEdiromFile.xsl -o:Edirom/content/structure/edirom.xml

# ADD SOURCES #
RUN mkdir Edirom/content/sources
RUN find Quellen -name "edirom-source*.xml" -exec sh -c 'xslt -s:"$1" -xsl:${SCRIPT_PATH}/injectSourceIds.xsl -o:"Edirom/content/structure/sources/$1"' _ {} \;

# COPY PREFS and PROPERTIES #
RUN mv Edirom/local.properties Edirom/prefs.xml Edirom/content

########################
# Build edirom content #
########################
FROM openjdk:25-jdk-bullseye AS build-content

RUN apt-get update \
    && apt-get install -y --no-install-recommends ant 

RUN git clone -b develop --single-branch --recursive https://github.com/Edirom/Edirom-Edition-Packaging.git

WORKDIR /Edirom-Edition-Packaging
COPY --from=prepare-content /app/Edirom/content .

RUN ant -Duri.edition=/Edirom-Edition-Packaging xar

########################
# Final output stage   #
########################
FROM alpine:latest AS final
COPY --from=build-content /Edirom-Edition-Packaging/dist/*.xar /output/