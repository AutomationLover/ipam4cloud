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

# Install dependencies if node_modules doesn't exist or is incomplete (for volume mounts)
# Then start the development server
CMD sh -c "if [ ! -d 'node_modules' ] || [ ! -f 'node_modules/@vue/cli-plugin-babel/package.json' ]; then echo 'Installing dependencies...' && npm install; fi && npm run serve"
