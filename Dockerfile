# Use slim python base
FROM python:3.12-slim

# Set environment vars
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build essentials (only if needed — slim image needs help to build wheels sometimes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create workdir
WORKDIR /app

# Copy your code (only what is needed)
COPY pyproject.toml .
COPY asg_runtime/ asg_runtime/

# Install the runtime itself (only the base dependencies, no dev extras)
RUN pip install --no-cache-dir .

# (Optional) Show what is installed (debugging)
RUN pip list

# Default command (can override at container run)
CMD ["python"]
