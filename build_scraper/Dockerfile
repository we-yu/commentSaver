# Use an official Python runtime as a parent image
FROM python:3.10

# add this line to install vim
RUN apt-get update && apt-get install -y \
    vim  

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
# EXPOSE 80

# Run scraper.py when the container launches
# ログイン後に手動で実行するのでコメントアウト
# CMD ["python", "scraper.py"]

# Dockerfile
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Define command to start bash
# ENTRYPOINT ["/bin/bash"]

