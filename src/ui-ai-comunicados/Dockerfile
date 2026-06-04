# Stage 1: Build the UI using Node.js
FROM node:20-slim AS build-stage

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy all source files
COPY . .

# Run the build script
RUN npm run build

# Stage 2: Serve the static files using Nginx
FROM nginx:stable-alpine

# Copy the built assets from the build stage to Nginx's public folder
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy a basic Nginx configuration to handle SPA routing
RUN echo 'server { \
    listen 8080; \
    server_name localhost; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Expose port 8080 (Cloud Run default)
EXPOSE 8080

# Use the entrypoint script to inject env vars at runtime
ENTRYPOINT ["/entrypoint.sh"]
