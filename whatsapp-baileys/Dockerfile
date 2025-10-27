FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --production

# Copy application files
COPY . .

# Create directory for auth credentials
RUN mkdir -p /app/auth_info

# Expose port (not needed for this service but good practice)
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
