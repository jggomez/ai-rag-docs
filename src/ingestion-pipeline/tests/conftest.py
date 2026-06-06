import os

# Solo configurar variables simuladas si no se forzó el test real de Firestore
if os.environ.get("RUN_FIRESTORE_TESTS") != "true":
    os.environ["GCP_PROJECT_ID"] = "dummy-project-id"
    os.environ["GOOGLE_CLOUD_PROJECT"] = "dummy-project-id"
    os.environ["GCLOUD_PROJECT"] = "dummy-project-id"
    os.environ["FIRESTORE_DATABASE_RECEIVED"] = "docs-recibidos"
    os.environ["FIRESTORE_DATABASE_SENT"] = "docs-enviados"
    os.environ["GOOGLE_API_KEY"] = "dummy-api-key"
    os.environ["METADATA_CSV_PATH"] = "dummy-metadata.csv"
