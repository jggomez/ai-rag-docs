#!/bin/bash
# ============================================================================
# Script: Create Firestore Vector Index
# Description: Creates a composite vector index on the documentos_chunks
#              collection in the docs-recibidos Firestore database.
#              Required for the RAG retriever's find_nearest vector search.
# Usage: ./scripts/create_vector_index.sh
# ============================================================================

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-devhack-3f0c2}"
DATABASE="docs-recibidos"
COLLECTION_GROUP="documentos_chunks"
VECTOR_FIELD="vector"
DIMENSION=768

echo "🔧 Creating Firestore vector index..."
echo "   Project:    ${PROJECT_ID}"
echo "   Database:   ${DATABASE}"
echo "   Collection: ${COLLECTION_GROUP}"
echo "   Field:      ${VECTOR_FIELD} (dimension: ${DIMENSION})"
echo ""

gcloud firestore indexes composite create \
  --database="${DATABASE}" \
  --collection-group="${COLLECTION_GROUP}" \
  --field-config="field-path=${VECTOR_FIELD},vector-config={\"dimension\":\"${DIMENSION}\",\"flat\":{}}" \
  --project="${PROJECT_ID}"

echo ""
echo "✅ Vector index creation initiated."
echo "   Note: Index creation may take a few minutes to complete."
echo "   Monitor progress at: https://console.cloud.google.com/firestore/indexes?project=${PROJECT_ID}&database=${DATABASE}"
