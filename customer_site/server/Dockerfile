# Build context is the repo root (needed to COPY the shared catalog/ package):
#   docker build -f customer_site/server/Dockerfile .

FROM python:3.11-slim

WORKDIR /app

COPY customer_site/server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY catalog ./catalog
COPY customer_site/server/app.py customer_site/server/data.py customer_site/server/stores.py customer_site/server/stock.py customer_site/server/sales.py ./

EXPOSE 8000

CMD ["gunicorn", "--preload", "--workers", "2", "--threads", "4", "-b", "0.0.0.0:8000", "--timeout", "120", "app:app"]
