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

# Index 1: numero_contrato + vector (for contract-only filter)
echo "📋 Index 1/3: numero_contrato + vector"
gcloud firestore indexes composite create \
  --database="${DATABASE}" \
  --collection-group="${COLLECTION_GROUP}" \
  --field-config="field-path=numero_contrato,order=ASCENDING" \
  --field-config="field-path=vector,vector-config={\"dimension\":\"768\",\"flat\":{}}" \
  --project="${PROJECT_ID}" &

# Index 2: numero_contrato + proceso + vector (for contract+process filter)
echo "📋 Index 2/3: numero_contrato + proceso + vector"
gcloud firestore indexes composite create \
  --database="${DATABASE}" \
  --collection-group="${COLLECTION_GROUP}" \
  --field-config="field-path=numero_contrato,order=ASCENDING" \
  --field-config="field-path=proceso,order=ASCENDING" \
  --field-config="field-path=vector,vector-config={\"dimension\":\"768\",\"flat\":{}}" \
  --project="${PROJECT_ID}" &

# Index 3: numero_contrato + proceso + frente_trabajo + vector (full filter)
echo "📋 Index 3/3: numero_contrato + proceso + frente_trabajo + vector"
gcloud firestore indexes composite create \
  --database="${DATABASE}" \
  --collection-group="${COLLECTION_GROUP}" \
  --field-config="field-path=numero_contrato,order=ASCENDING" \
  --field-config="field-path=proceso,order=ASCENDING" \
  --field-config="field-path=frente_trabajo,order=ASCENDING" \
  --field-config="field-path=vector,vector-config={\"dimension\":\"768\",\"flat\":{}}" \
  --project="${PROJECT_ID}" &

echo ""
echo "⏳ Waiting for all index creation requests to complete..."
wait

echo ""
echo "✅ All composite index creation requests submitted."
echo "   Monitor progress at: https://console.cloud.google.com/firestore/indexes?project=${PROJECT_ID}&database=${DATABASE}"
