FROM python:3.12-slim

# Install basic system tools
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (The modern, stable way)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Upgrade pip and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Create templates folder if it doesn't exist (prevents Flask crash)
RUN mkdir -p templates

# Expose the port (Koyeb looks for this)
EXPOSE 8000

# Start the application
CMD ["python", "whatsappSynchronizer.py"]