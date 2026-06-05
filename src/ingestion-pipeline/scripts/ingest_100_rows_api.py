import csv
import json
import urllib.request
import urllib.error
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "..", "resources", "Comunicaciones.csv")
API_URL = "http://localhost:8080/api/v1/ingest"

def post_ingest(payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as res:
            response_data = json.loads(res.read().decode("utf-8"))
            print(f"  SUCCESS: Ingested {payload['document_type']} -> ID: {response_data.get('document_id')}")
            return True
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        print(f"  FAILED: HTTP {e.code} - {error_msg}")
        return False
    except Exception as e:
        print(f"  FAILED: Error connecting: {str(e)}")
        return False

def main():
    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found at: {CSV_PATH}")
        return

    print(f"Reading from CSV: {CSV_PATH}")
    with open(CSV_PATH, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Get first 100 data rows
    first_100_rows = rows[:100]
    print(f"Processing first {len(first_100_rows)} rows...")

    for index, row in enumerate(first_100_rows, start=1):
        draft_id = row.get("Id borradores", "").strip() or f"row-{index}"
        print(f"\n[{index}/100] Row ID: {draft_id}")

        # Extract/clean URLs and document code names
        recibidas_url = row.get("url Recibidas", "").strip()
        has_valid_recibidas = recibidas_url and recibidas_url.startswith("http") and "Sin" not in recibidas_url
        recibidas_name = row.get("Recibidas", "").strip()

        enviadas_url = (row.get("Ubicacion filtradas") or row.get("Ubicacion Enviadas") or "").strip()
        has_valid_enviadas = enviadas_url and enviadas_url.startswith("http") and "Sin" not in enviadas_url
        enviadas_name = row.get("Enviadas", "").strip()


        # Call API for RECEIVED document
        if has_valid_recibidas:
            print(f" -> Ingesting RECIBIDA: {recibidas_url} (name: {recibidas_name})")
            rec_metadata = {
                "sender": row.get("Para", "UNKNOWN").strip(),
                "contract_number": row.get("Contrato", "UNKNOWN").strip(),
                "work_front": row.get("Frente", "GENERAL").strip(),
                "document_date": row.get("Fecha", "UNKNOWN").strip(),
                "process": row.get("Proceso", "INBOX").strip(),
                "response_file_url": enviadas_url if has_valid_enviadas else (enviadas_name or None),
                "id_borrador": draft_id
            }
            post_ingest({
                "url": recibidas_url,
                "document_type": "received",
                "filename": recibidas_name or None,
                "metadata": rec_metadata
            })
        else:
            print(" -> No valid URL for Recibidas")

        # Call API for SENT document
        if has_valid_enviadas:
            print(f" -> Ingesting ENVIADA: {enviadas_url} (name: {enviadas_name})")
            sent_metadata = {
                "sender": row.get("Para", "UNKNOWN").strip(),
                "contract_number": row.get("Contrato", "UNKNOWN").strip(),
                "work_front": row.get("Frente", "GENERAL").strip(),
                "document_date": row.get("Fecha", "UNKNOWN").strip(),
                "process": row.get("Proceso", "INBOX").strip(),
                "response_file_url": recibidas_url if has_valid_recibidas else (recibidas_name or None),
                "id_borrador": draft_id
            }
            post_ingest({
                "url": enviadas_url,
                "document_type": "sent",
                "filename": enviadas_name or None,
                "metadata": sent_metadata
            })
        else:
            print(" -> No valid URL for Enviadas/Filtradas")

if __name__ == "__main__":
    main()
