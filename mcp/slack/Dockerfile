# Mirage Slack Bot Dockerfile for fly.io

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY mcp/slack/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code + core library from repo root context
COPY mcp/slack ./slack
COPY mirage_core ./mirage_core

ENV PYTHONPATH=/app
WORKDIR /app/slack

EXPOSE 3000

CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "2", "--timeout", "120", "server:flask_app"]
