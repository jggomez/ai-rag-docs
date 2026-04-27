import csv
import requests
import os
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_URL = os.environ.get("INGEST_API_URL", "http://localhost:8080/ingest")
DEFAULT_BUCKET = os.environ.get("DEFAULT_INGEST_BUCKET", "unite-data-ingestion")

def batch_ingest(csv_path: str, bucket: str):
    """
    Reads the CSV and triggers ingestion via API for each row.
    """
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found: {csv_path}")
        return

    success_count = 0
    fail_count = 0

    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 'Enviadas' is our primary identifier/GCS object suffix
                doc_id = row.get("Enviadas", "").strip()
                if not doc_id:
                    continue

                # Construct the GCS object name. 
                # Assuming they are stored in COMMUNICATION_RECEIVED/ with .pdf extension
                object_name = f"COMMUNICATION_RECEIVED/{doc_id}.pdf"
                
                payload = {
                    "bucket": bucket,
                    "object_name": object_name,
                    "sender": row.get("Para", "UNKNOWN"),
                    "contract_number": row.get("Contrato", "UNKNOWN"),
                    "work_front": row.get("Frente", "GENERAL"),
                    "document_date": row.get("Fecha", "UNKNOWN"),
                    "process": row.get("Proceso", "INBOX"),
                    "response_file_url": doc_id # The field in the CSV itself
                }

                logger.info(f"Triggering ingestion for: {doc_id}")
                
                try:
                    response = requests.post(API_URL, json=payload)
                    if response.status_code == 200:
                        logger.info(f"Successfully triggered {doc_id}")
                        success_count += 1
                    else:
                        logger.error(f"Failed to trigger {doc_id}: {response.text}")
                        fail_count += 1
                except Exception as e:
                    logger.error(f"Error calling API for {doc_id}: {str(e)}")
                    fail_count += 1

        logger.info(f"Batch processing finished. Success: {success_count}, Failed: {fail_count}")

    except Exception as e:
        logger.error(f"Error reading CSV: {str(e)}")

def trigger_batch():
    """
    Triggers the batch ingestion process via the server-side API endpoint.
    """
    logger.info(f"Triggering server-side batch ingestion at: {API_URL}")
    
    try:
        response = requests.post(API_URL)
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Batch ingestion started successfully.")
            logger.info(f"Result: {result}")
        else:
            logger.error(f"Failed to trigger batch ingestion: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error calling API: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch ingest communications from CSV")
    parser.add_argument("--csv", default="src/resources/Comunicaciones.csv", help="Path to the metadata CSV")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET, help="GCS bucket where PDFs are stored")
    parser.add_argument("--mode", choices=["client", "server"], default="client", help="Ingestion mode: client (row by row) or server (bulk)")
    
    args = parser.parse_args()
    
    if args.mode == "server":
        trigger_batch()
    else:
        batch_ingest(args.csv, args.bucket)
