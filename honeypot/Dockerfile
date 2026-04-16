FROM python:3.10-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root user (important)
RUN useradd -m honeypotuser

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy honeypot code
COPY . .

# Create required dirs
RUN mkdir -p logs sessions \
    && chown -R honeypotuser:honeypotuser /app

USER honeypotuser

EXPOSE 5000

CMD ["python", "app.py"]
