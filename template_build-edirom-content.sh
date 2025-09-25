#!/bin/bash
docker build-xar -f build-edirom/buildEdiromContent.Dockerfile -t edirom-builder .
rm -rf build-xar
mkdir -p build-xar
CONTAINER_ID=$(docker create edirom-builder)
docker cp $CONTAINER_ID:/output/. ./build-xar/
docker rm $CONTAINER_ID
echo "XAR files copied to ./build-xar/"