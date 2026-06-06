#!/bin/bash
# ============================================================================
# Script: Create Firestore Composite Vector Indexes
# Description: Creates composite indexes combining metadata filters with
#              vector search on the documentos_chunks collection.
#              Required for hybrid search (metadata + vector similarity).
# Usage: ./scripts/create_composite_indexes.sh
# ============================================================================

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-devhack-3f0c2}"
DATABASE="docs-recibidos"
COLLECTION_GROUP="documentos_chunks"

echo "🔧 Creating composite vector indexes for hybrid search..."
echo "   Project:    ${PROJECT_ID}"
echo "   Database:   ${DATABASE}"
echo "   Collection: ${COLLECTION_GROUP}"
echo ""

# Index: frente_trabajo + vector (for work front filtered vector searches)
echo "📋 Index: frente_trabajo + vector"
gcloud firestore indexes composite create \
  --database="${DATABASE}" \
  --collection-group="${COLLECTION_GROUP}" \
  --query-scope=COLLECTION \
  --field-config="field-path=frente_trabajo,order=ASCENDING" \
  --field-config="field-path=vector,vector-config={\"dimension\":\"768\",\"flat\":{}}" \
  --project="${PROJECT_ID}"

echo ""
echo "✅ Composite index creation request submitted."
echo "   Monitor progress at: https://console.cloud.google.com/firestore/indexes?project=${PROJECT_ID}&database=${DATABASE}"
