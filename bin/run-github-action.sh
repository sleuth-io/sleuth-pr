#!/bin/bash

echo "Creating database tables"
python /app/manage.py migrate

echo "Processing the event"
python /app/manage.py on_github_action