# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container at /app
COPY . .

# Define environment variable for the project root
ENV PYTHONPATH=/app

# Command to run the application
# Assuming main.py is the primary entry point for your automation tasks.
# If your application needs to serve HTTP requests (e.g., for Cloud Run),
# this command will need to be adjusted to start a web server (e.g., Flask, FastAPI).
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]
