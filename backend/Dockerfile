# REI API. Build from the repository root (the image also needs database/):
#   docker build -f backend/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv/backend

WORKDIR /srv

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY database database
COPY backend backend

RUN useradd --create-home rei && chown -R rei /srv
USER rei

EXPOSE 8000
# Keep-alive is longer than the web app's proxy keeps idle connections.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75"]
