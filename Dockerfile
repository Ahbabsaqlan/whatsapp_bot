FROM python:3.12-slim

# Install system dependencies for Chrome and Postgres
RUN apt-get update && apt-get install -y \
    wget gnupg unzip curl libpq-dev gcc \
    libnss3 libatk-bridge2.0-0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libasound2 libpangocairo-1.0-0 libgtk-3-0 \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Ensure we have the latest pip
RUN pip install --no-cache-dir --upgrade pip

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# IMPORTANT: Ensure the templates folder exists in the build
RUN mkdir -p templates

EXPOSE 8000

# Run with 0.0.0.0 so Koyeb can route traffic to it
CMD ["python", "whatsappSynchronizer.py"]