# Use an official lightweight Python image
FROM python:3.11-slim

# Set environment variables for best practices
ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    APP_HOME=/app

# Set the working directory inside the container
WORKDIR $APP_HOME

# Copy only the necessary files
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . .

# Expose the application's port (Flask typically runs on 5000)
EXPOSE 8000

# Use Gunicorn with Uvicorn workers for async & scalable performance
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
