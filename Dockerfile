# Use an official Python runtime
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy local files to container
COPY . /app

# Install system dependencies for PyPDF2 and other libs
RUN apt-get update && apt-get install -y \
    build-essential \
    libpoppler-cpp-dev \
    && apt-get clean

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Streamlit port
EXPOSE 8080



# Run Streamlit app
CMD streamlit run App.py --server.port=8080 --server.address=0.0.0.0
