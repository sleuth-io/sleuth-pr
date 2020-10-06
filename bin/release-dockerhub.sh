#!/bin/bash

docker login -u $DOCKERHUB_USERNAME -p $DOCKERHUB_API_KEY

VERSION=`python setup.py --version`
echo "Building $VERSION"
docker build -t sleuthpr-dev:$VERSION --build-arg VERSION=$VERSION .
docker tag sleuthpr-dev:$VERSION mrdonbrown/sleuth-pr-dev:$VERSION

echo "Pushing $VERSION"
docker push mrdonbrown/sleuth-pr-dev:$VERSION