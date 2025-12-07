# Resume Tailor - Dockerfile
# Python 3.11 + TeX Live for LaTeX compilation (Local Development Version)

FROM python:3.11-slim

# Install system dependencies and TeX Live
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output directory
RUN mkdir -p output data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set entrypoint to python main.py so arguments are appended
ENTRYPOINT ["python", "main.py"]

# Default arguments if none provided
CMD ["--help"]

