# Use official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy your bot code into the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "bot.py"]
