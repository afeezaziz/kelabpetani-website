# Simple production-ready image using Gunicorn
FROM python:3.11-slim

# Prevents Python from writing .pyc files and enables stdout/err unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose Gunicorn port
EXPOSE 8000

# Default command runs Gunicorn with the app factory via wsgi.py
CMD ["gunicorn", "-b", "0.0.0.0:8000", "wsgi:app"]
