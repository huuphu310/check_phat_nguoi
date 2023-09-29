FROM python:3.10.13-alpine
LABEL authors="phunh"

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install dependencies and any other necessary packages
# For Alpine, you might need to install some build dependencies for certain Python packages
RUN apk add --no-cache --virtual .build-deps gcc musl-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps

# Now copy the rest of the code
COPY . .

# Command to run on container start
CMD ["python", "./main.py"]