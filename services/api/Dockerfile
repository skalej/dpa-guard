FROM python:3.11-slim

WORKDIR /app

# System deps (optional but useful)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Install python deps first (better layer caching)
COPY pyproject.toml /app/pyproject.toml

# If you also have a lock file, copy it too:
# COPY poetry.lock /app/poetry.lock

RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir .

# Copy application code
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

EXPOSE 8000

# Run API
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
