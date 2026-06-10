# Resume Tailor - Dockerfile
# Python 3.11 + TeX Live for LaTeX compilation (Local Development Version)

FROM python:3.11-slim

# Install system dependencies and TeX Live
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (LTS) + the Claude Code CLI, which the claude-agent-sdk
# spawns as a subprocess to drive inference against the Claude subscription.
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @anthropic-ai/claude-code \
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

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port for FastAPI
EXPOSE 8000

# Run the entrypoint script (handles migrations + server start)
CMD ["./entrypoint.sh"]

