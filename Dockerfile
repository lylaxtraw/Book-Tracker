FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so edits to the app do not bust the layer cache.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

# The database lives on a mounted volume, not in the image -- an image rebuild
# must never take the library with it.
ENV DATABASE_URL=sqlite:////data/booktracker.db
VOLUME ["/data"]

EXPOSE 8000

# One worker on purpose: SQLite does not enjoy several writers.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
