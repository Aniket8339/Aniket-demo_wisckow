# Use Ubuntu as base image
FROM ubuntu:20.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && \
    apt-get install -y \
    cowsay \
    fortune-mod \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Set PATH to include cowsay
ENV PATH="/usr/games:${PATH}"

# Create app directory
WORKDIR /app

# Copy the wisecow script
COPY wisecow.sh /app/

# Make the script executable
RUN chmod +x /app/wisecow.sh

# Expose port 4499
EXPOSE 4499

# Run the application
CMD ["/app/wisecow.sh"]