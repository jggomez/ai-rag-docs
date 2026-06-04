#!/bin/bash
# Script to run local MLflow Tracking Server

echo "Starting MLflow Tracking Server..."
echo ""
echo "  ✅ Open your browser at: http://localhost:5001"
echo ""
echo "Data will be stored in ./mlflow.db and ./mlartifacts"

uvx mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --artifacts-destination ./mlartifacts \
  --serve-artifacts \
  --host 127.0.0.1 \
  --port 5001 \
  --cors-allowed-origins "http://localhost:5001,http://127.0.0.1:5001"
