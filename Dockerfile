FROM mrdonbrown/sleuth-pr-base:base-1661552

WORKDIR /app

ARG VERSION

COPY requirements.txt .
COPY setup.py .
COPY setup.cfg .
RUN echo "Version: $VERSION" > /app/PKG-INFO


RUN pip install -qq -e .[prod]

COPY manage.py .
COPY bin/run-github-action.sh .
COPY sleuthpr /app/sleuthpr
COPY app /app/app

ENV DJANGO_SETTINGS_MODULE="app.settings.github_action"
EXPOSE 8125/udp
EXPOSE 8080/tcp

CMD ["/app/run-github-action.sh"]

