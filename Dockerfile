# Use a lightweight Python base
FROM python:3.9-slim

# 1. Install FFmpeg and Arabic Font packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-noto-core \
    fonts-noto-ui-arabic \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy your project files
COPY . .

# 4. Set the command to run your bot
CMD ["python", "app.py"]
