# Use an official Python runtime as a parent image
FROM python:3.9-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED 1

# Chrome 브라우저 및 필요한 라이브러리 설치
RUN apt-get update && apt-get install -y wget unzip     chromium-driver     chromium     libglib2.0-0     libnss3     libfontconfig1     libxrender1     libxext6     libxrandr2     libxfixes3     libxi6     libgconf-2-4     libatk1.0-0     libatk-bridge2.0-0     libcups2     libdrm-dev     libgbm-dev     libasound2     libdbus-1-3     libexpat1     libstdc++6     libx11-6     libxcomposite1     libxcursor1     libxdamage1     libxft2     libxinerama1     libxrandr2     libxss1     libxtst6     libappindicator1     libgdk-pixbuf2.0-0     libgtk-3-0     libnotify4     libpng16-16     libwebp6     libwebpdemux2     libwebrtc-audio-processing1     fonts-liberation libappindicator3-1 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libxss1 libxtst6 libatk-bridge2.0-0 libcups2 libdrm-dev libgbm-dev libasound2 libdbus-1-3 libexpat1 libstdc++6 libx11-6 libxcursor1 libxft2 libxinerama1 libgdk-pixbuf2.0-0 libgtk-3-0 libnotify4 libpng16-16 libwebp6 libwebpdemux2 --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN wget -O /tmp/chromedriver.zip "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/120.0.6099.109/linux64/chromedriver-linux64.zip"     && unzip /tmp/chromedriver.zip -d /usr/local/bin     && rm /tmp/chromedriver.zip     && chmod +x /usr/local/bin/chromedriver-linux64/chromedriver     && ln -s /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver


# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container at /app
COPY . .

# Define environment variable for the project root
ENV PYTHONPATH=/app

# Command to run the application with Gunicorn
# The PORT environment variable is automatically provided by Cloud Run
ENTRYPOINT ["/bin/sh"]
