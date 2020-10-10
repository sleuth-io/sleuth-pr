#!/bin/bash

docker login -u $DOCKERHUB_USERNAME -p $DOCKERHUB_API_KEY

VERSION=base-`git rev-parse --short HEAD`
echo "Building $VERSION"
docker build -f base.Dockerfile -t base-dev:$VERSION .
docker tag base-dev:$VERSION mrdonbrown/sleuth-pr-base:$VERSION

echo "Pushing $VERSION"
docker push mrdonbrown/sleuth-pr-base:$VERSION