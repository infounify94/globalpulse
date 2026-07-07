# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
# Mock requirements install since requirements.txt might not be fully fleshed out yet
# In a real build, we'd run: RUN pip install --no-cache-dir -r requirements.txt
RUN pip install fastapi uvicorn streamlit pandas numpy scikit-learn sqlalchemy xgboost lightgbm plotly

# Copy the rest of the application
COPY . .

# Expose ports for FastAPI (8000) and Streamlit (8501)
EXPOSE 8000
EXPOSE 8501

# The CMD will be overridden by docker-compose for specific services
CMD ["bash"]
