##########################
# Prepare edirom content #
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

######################
# Curl Edirom Online #
######################

FROM curlimages/curl:latest AS curl-edirom
WORKDIR /downloads

RUN echo "Downloading Edirom Online Frontend"
RUN curl -L -o eof-ewk-build.xar "https://github.com/korngold-werkausgabe/Edirom-Online-Frontend_EWK-WA/releases/download/latest/eof-ewk-latest.xar" 

RUN echo "Downloading Edirom Online Backend"
RUN curl -L -o eob-ewk-build.xar "https://github.com/korngold-werkausgabe/Edirom-Online-Backend_EWK-WA/releases/download/latest/eob-ewk-latest.xar" 

#####################################
# Run exist-db and add xar-packages #
#####################################
FROM stadlerpeter/existdb:6.3.0

COPY --chown=wegajetty --from=curl-edirom /downloads/*.xar ${EXIST_HOME}/autodeploy/
COPY --chown=wegajetty --from=build-content /Edirom-Edition-Packaging/dist/*.xar ${EXIST_HOME}/autodeploy/
