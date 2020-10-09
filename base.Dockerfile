FROM python:3.8-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY bin/install-re2.sh .
RUN apt update \
    && apt -y install wget unzip build-essential \
    && install-re2.sh

