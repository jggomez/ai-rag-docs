#!/bin/sh

# Create the config.js file using environment variables
# This script is executed at container startup in Cloud Run

cat <<EOF > /usr/share/nginx/html/config.js
window.config = {
  VITE_INGESTION_API_URL: "${VITE_INGESTION_API_URL:-http://localhost:8080}",
  VITE_AGENT_API_URL: "${VITE_AGENT_API_URL:-http://localhost:8000}"
};
EOF

echo "Generated /usr/share/nginx/html/config.js with runtime environment variables."

# Start Nginx
exec nginx -g "daemon off;"
