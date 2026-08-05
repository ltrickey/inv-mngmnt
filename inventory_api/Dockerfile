# Build context is the repo root (needed to COPY the shared catalog/ package):
#   docker build -f inventory_api/Dockerfile .

FROM python:3.11-slim

WORKDIR /app

COPY inventory_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY catalog ./catalog
COPY inventory_api/config.py inventory_api/inventory.py inventory_api/inventory_dao.py inventory_api/main.py inventory_api/sales_dao.py ./

EXPOSE 9000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
