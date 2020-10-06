FROM python:3.8-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY statsd-fake.py /app/statsd-fake.py

COPY requirements.txt .
RUN pip install -qq -r requirements.txt

EXPOSE 8125/udp
EXPOSE 8080/tcp

ENV FLASK_APP=/app/statsd-fake.py

CMD ["flask", "run", "--host", "0.0.0.0", "--port", "8080"]

