# Quickstart: Restrict CSV Ingestion Columns

This guide describes how to verify the updated ingestion pipeline with the restricted CSV schema.

## Prerequisites
Ensure the environment is configured:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
export GEMINI_API_KEY="your-api-key"
```

## Running the Ingestion Verification

1. **Create a Test CSV File**:
   Create a test CSV named `test_restricted.csv` with only the 7 allowed columns:
   ```csv
   Id borradores,Fecha,Frente,Recibidas,url Recibidas,Enviadas,Ubicacion filtradas
   99990001,05/06/2026,Frente Test,REC-0001,https://drive.google.com/file/d/1HPlEkEofIcUBbj4bjY60XEDGwdgUAe3U/view,SEN-0001,https://drive.google.com/file/d/1wX4UQTO7NKmRNC-bX4scR9PsTHHru7lp/view
   99990002,05/06/2026,Frente Test,REC-0002,Sin URL origen,SEN-0002,https://drive.google.com/file/d/1wX4UQTO7NKmRNC-bX4scR9PsTHHru7lp/view
   ```

2. **Run Ingestion Command**:
   Execute the ingestion command (or test suite) with the created CSV:
   ```bash
   pytest tests/integration/test_batch_ingest.py
   ```

3. **Verify Results in Database**:
   * For row `99990001`: Both RECEIVED (`99990001_REC`) and SENT (`99990001_SEN`) documents must be present in Firestore.
   * For row `99990002`: Only the SENT (`99990002_SEN`) document must be present. The RECEIVED document must be skipped entirely.
   * Check that unmapped fields (e.g. `Para`, `Contrato`, `Proceso`) are set to default values like `"UNKNOWN"`.
