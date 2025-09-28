# Dockerfile — Render-ready Selenium + Chrome + Chromedriver
FROM python:3.10-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Chrome & Chromedriver dependencies
RUN apt-get update && apt-get install -y \
    wget unzip gnupg ca-certificates curl \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libxshmfence1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (stable)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install Chromedriver (match Chrome version)
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') \
    && CHROMEDRIVER_VERSION=$(echo $CHROME_VERSION | cut -d. -f1) \
    && wget -q "https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver.zip /usr/local/bin/chromedriver-linux64

# Set display port for Selenium
ENV DISPLAY=:99

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . /app
WORKDIR /app

# Default command (Render runs this as web service)
CMD ["python", "main.py"]
