#!/bin/bash

docker login -u $DOCKERHUB_USERNAME -p $DOCKERHUB_API_KEY

VERSION=base-`git rev-parse --short HEAD`
echo "Building $VERSION"
docker build -t base-dev:$VERSION --build-arg VERSION=$VERSION .
docker tag base-dev:$VERSION mrdonbrown/sleuth-pr-base:$VERSION

echo "Pushing $VERSION"
docker push mrdonbrown/sleuth-pr-base:$VERSION