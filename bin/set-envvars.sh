#!/bin/bash

echo "Exporting env vars"
export $(cat config/dev/env | sed 's/#.*//g' | xargs)
export GITHUB_APP_PRIVATE_KEY=$(cat config/dev/private-key.pem)
