FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose port 8081
EXPOSE 8081

# Start development server
CMD ["npm", "run", "serve"]
