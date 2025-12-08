# Use the official Playwright Python image which includes browsers and dependencies
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (specifically chromium to keep image size reasonable)
# The base image might have them, but this ensures they match the python package version
RUN playwright install chromium

# Copy the rest of the application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the entrypoint
ENTRYPOINT ["python", "main.py"]

# Default arguments
CMD ["--help"]
