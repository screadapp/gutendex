FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    bzip2 \
    rsync \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Run collectstatic during build (with dummy env vars to satisfy settings.py)
RUN SECRET_KEY=dummy \
    DATABASE_URL=sqlite:////tmp/dummy.db \
    ALLOWED_HOSTS=* \
    STATIC_ROOT=/app/staticfiles \
    python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD python manage.py migrate && gunicorn gutendex.wsgi --bind 0.0.0.0:${PORT:-8000}
