FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

EXPOSE 8080

# Install dependencies if node_modules doesn't exist (for volume mounts)
# Then start the development server
CMD sh -c "if [ ! -d 'node_modules' ] || [ ! -f 'node_modules/.package-lock.json' ]; then npm install; fi && npm run serve"

