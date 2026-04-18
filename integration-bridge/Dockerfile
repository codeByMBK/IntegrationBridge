FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-create the file_drop directories so the watcher has a valid path
# even before the host volume is mounted by docker compose.
RUN mkdir -p /app/file_drop/processed

COPY . .

CMD ["uvicorn", "main:asgi_app", "--host", "0.0.0.0", "--port", "8000"]
