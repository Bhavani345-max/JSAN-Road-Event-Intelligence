# REI API. Build from the repository root:
#   docker build -f infrastructure/docker/api.Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv:/srv/apps/api

WORKDIR /srv

COPY apps/api/requirements.txt apps/api/requirements.txt
RUN pip install --no-cache-dir -r apps/api/requirements.txt

COPY packages packages
COPY connectors connectors
COPY services services
COPY database database
COPY apps/api apps/api

RUN useradd --create-home rei && chown -R rei /srv
USER rei

EXPOSE 8000
# Keep-alive is longer than the web app's proxy keeps idle connections.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75"]
