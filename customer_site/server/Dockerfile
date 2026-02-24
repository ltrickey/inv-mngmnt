FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py data.py stores.py stock.py sales.py ./

EXPOSE 8000

CMD ["gunicorn", "--preload", "--workers", "2", "--threads", "4", "-b", "0.0.0.0:8000", "--timeout", "120", "app:app"]
