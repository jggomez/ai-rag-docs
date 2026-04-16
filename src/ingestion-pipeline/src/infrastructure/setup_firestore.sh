#!/bin/bash
# Script to configure Firestore Vector Index for the RAG pipeline

PROJECT_ID=$(gcloud config get-value project)
DATABASE_ID="(default)"

echo "Creating Vector Index for 'document_chunks' collection..."

# Create a vector index on the 'embedding' field
# Note: This command assumes gcloud beta or specific version support for Vector Search
gcloud alpha firestore indexes composite create \
    --project=$PROJECT_ID \
    --collection-group=document_chunks \
    --query-scope=COLLECTION \
    --field-config=field-path=embedding,vector-config='{"dimension":"768", "flat": "{}"}' \
    --field-config=field-path=contract_number,order=ASCENDING

echo "Vector index creation initiated. It may take a few minutes to be ready."
