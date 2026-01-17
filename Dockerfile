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

# Expose port
EXPOSE 8000

# Run migrations, collect static, and start server
CMD python manage.py migrate && python manage.py collectstatic --noinput && gunicorn gutendex.wsgi --bind 0.0.0.0:${PORT:-8000}
