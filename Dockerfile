FROM python:3.10-slim

# Install dependencies
RUN apt-get update && apt-get install -y wget unzip curl chromium chromium-driver

# Set display port to avoid errors
ENV DISPLAY=:99

# Workdir
WORKDIR /app

# Copy files
COPY . .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
