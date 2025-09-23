#!/bin/bash
docker build -f build-edirom/buildEdiromContent.Dockerfile -t edirom-builder .
rm -rf build
mkdir -p build
CONTAINER_ID=$(docker create edirom-builder)
docker cp $CONTAINER_ID:/output/. ./build/
docker rm $CONTAINER_ID
echo "XAR files copied to ./build/"