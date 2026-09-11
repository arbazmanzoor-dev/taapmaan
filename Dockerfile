FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/app backend/app
COPY backend/data/cities.json backend/data/cities.json
COPY backend/data/census backend/data/census
COPY backend/data/climate backend/data/climate
COPY backend/data/models backend/data/models
COPY backend/scripts backend/scripts
COPY index.html index.html

ENV TAAPMAAN_DB=/app/backend/data/taapmaan.db
EXPOSE 8000
WORKDIR /app/backend
# Render terminates HTTPS at its proxy; trusting X-Forwarded-Proto lets the app
# see https and mark the operator cookie Secure.
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
