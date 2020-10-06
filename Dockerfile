FROM python:3.8-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

ARG VERSION
COPY requirements.txt .
COPY setup.py .
COPY setup.cfg .
RUN echo "Version: $VERSION" > /app/PKG-INFO
RUN pip install -qq -r requirements.txt

COPY manage.py .
COPY sleuthpr /app/sleuthpr
COPY app /app/app

ENV DJANGO_SETTINGS_MODULE="app.settings.github_action"
EXPOSE 8125/udp
EXPOSE 8080/tcp

CMD ["python", "manage.py", "on_github_action"]

