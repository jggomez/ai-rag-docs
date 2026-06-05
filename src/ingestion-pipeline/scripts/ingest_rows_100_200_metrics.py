import os
import sys
import csv
import time
import logging
import traceback
from pathlib import Path
from dotenv import load_dotenv

# Set project root in path to import src modules correctly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load configuration and environment variables
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from google import genai
from google.genai import types
import mlflow

# Pricing constants (per token)
OCR_INPUT_COST_PER_TOKEN = 0.075 / 1_000_000
OCR_OUTPUT_COST_PER_TOKEN = 0.30 / 1_000_000
EMBEDDING_INPUT_COST_PER_TOKEN = 0.025 / 1_000_000

class GeminiMetricsTracker:
    def __init__(self):
        self.ocr_calls = 0
        self.ocr_input_tokens = 0
        self.ocr_output_tokens = 0
        self.ocr_total_time = 0.0
        
        self.embed_calls = 0
        self.embed_input_tokens = 0
        self.embed_total_time = 0.0

        self.ocr_cost = 0.0
        self.embed_cost = 0.0
        self.total_cost = 0.0

        self.row_metrics = []

    def wrap_client(self, client):
        original_generate = client.models.generate_content
        original_embed = client.models.embed_content

        def tracked_generate(*args, **kwargs):
            self.ocr_calls += 1
            start = time.time()
            try:
                response = original_generate(*args, **kwargs)
                duration = time.time() - start
                self.ocr_total_time += duration
                
                input_t = 0
                output_t = 0
                if response.usage_metadata:
                    input_t = response.usage_metadata.prompt_token_count
                    output_t = response.usage_metadata.candidates_token_count
                    self.ocr_input_tokens += input_t
                    self.ocr_output_tokens += output_t

                cost = (input_t * OCR_INPUT_COST_PER_TOKEN) + (output_t * OCR_OUTPUT_COST_PER_TOKEN)
                self.ocr_cost += cost
                self.total_cost += cost

                # Save metrics for current call context if needed
                if hasattr(self, "current_row_id"):
                    self.row_metrics.append({
                        "row_id": self.current_row_id,
                        "type": "OCR",
                        "model": kwargs.get("model") or (args[0] if len(args) > 0 else "unknown"),
                        "input_tokens": input_t,
                        "output_tokens": output_t,
                        "latency_sec": duration,
                        "cost_usd": cost,
                        "success": True,
                        "error": None
                    })
                
                return response
            except Exception as e:
                duration = time.time() - start
                if hasattr(self, "current_row_id"):
                    self.row_metrics.append({
                        "row_id": self.current_row_id,
                        "type": "OCR",
                        "model": kwargs.get("model") or (args[0] if len(args) > 0 else "unknown"),
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "latency_sec": duration,
                        "cost_usd": 0.0,
                        "success": False,
                        "error": str(e)
                    })
                raise e

        def tracked_embed(*args, **kwargs):
            self.embed_calls += 1
            start = time.time()
            try:
                contents = kwargs.get("contents") or (args[1] if len(args) > 1 else None)
                model = kwargs.get("model") or (args[0] if len(args) > 0 else None)
                
                input_t = 0
                if contents:
                    try:
                        # Request the actual token count from the API
                        count_res = client.models.count_tokens(model=model, contents=contents)
                        input_t = count_res.total_tokens
                    except Exception as e:
                        # Fallback heuristic (roughly 1 token per 4 characters)
                        input_t = len(str(contents)) // 4
                
                self.embed_input_tokens += input_t
                cost = input_t * EMBEDDING_INPUT_COST_PER_TOKEN
                self.embed_cost += cost
                self.total_cost += cost

                response = original_embed(*args, **kwargs)
                duration = time.time() - start
                self.embed_total_time += duration

                if hasattr(self, "current_row_id"):
                    self.row_metrics.append({
                        "row_id": self.current_row_id,
                        "type": "EMBEDDING",
                        "model": model or "unknown",
                        "input_tokens": input_t,
                        "output_tokens": 0,
                        "latency_sec": duration,
                        "cost_usd": cost,
                        "success": True,
                        "error": None
                    })

                return response
            except Exception as e:
                duration = time.time() - start
                if hasattr(self, "current_row_id"):
                    self.row_metrics.append({
                        "row_id": self.current_row_id,
                        "type": "EMBEDDING",
                        "model": model or "unknown",
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "latency_sec": duration,
                        "cost_usd": 0.0,
                        "success": False,
                        "error": str(e)
                    })
                raise e

        client.models.generate_content = tracked_generate
        client.models.embed_content = tracked_embed
        return client

# Global metrics tracker
tracker = GeminiMetricsTracker()

# Monkeypatch genai.Client initialization to automatically wrap all new client instances
original_init = genai.Client.__init__
def patched_init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    tracker.wrap_client(self)

genai.Client.__init__ = patched_init

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingest_rows_100_200_metrics")

def run_metrics_ingest():
    from src.config import settings
    from src.repositories.document_repo import RoutingFirestoreDocumentRepository
    from src.usecases.builder import PipelineBuilder
    from src.usecases.ingest_document import IngestDocumentCommand
    from src.domain.factory import SourceDocumentFactory
    from src.domain.enums import DocumentStatus

    # Configure MLflow
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5001")
    mlflow.set_tracking_uri(tracking_uri)
    experiment_name = "ingestion-pipeline"
    mlflow.set_experiment(experiment_name)
    
    # Auto logging
    mlflow.langchain.autolog()
    mlflow.gemini.autolog()

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "Comunicaciones.csv")
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found at: {csv_path}")
        return

    logger.info(f"Reading from CSV: {csv_path}")
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Slice indices 100 to 200 (inclusive) - Total 101 rows
    start_idx = 100
    end_idx = 200
    target_rows = rows[start_idx:end_idx+1]
    
    logger.info(f"Targeting row indices {start_idx} to {end_idx} (total {len(target_rows)} rows)")

    # Setup repositories and services
    document_repo = RoutingFirestoreDocumentRepository(
        database_received=settings.firestore_database_received,
        database_sent=settings.firestore_database_sent
    )
    pipeline_builder = PipelineBuilder(settings)
    
    # We construct pipelines on the fly for each document using the builder
    ingest_command = IngestDocumentCommand(
        document_repo=document_repo,
        pipeline_builder=pipeline_builder
    )

    processed_rows = []
    success_docs_count = 0
    failed_docs_count = 0
    total_docs_count = 0

    print("\n" + "="*80)
    print(f"STARTING METRIC MEASURING INGESTION (ROWS {start_idx} TO {end_idx})")
    print("="*80)

    start_time = time.time()

    # Start MLflow run
    with mlflow.start_run(run_name=f"ingest_rows_{start_idx}_{end_idx}") as run:
        mlflow.log_param("start_idx", start_idx)
        mlflow.log_param("end_idx", end_idx)
        mlflow.log_param("total_target_rows", len(target_rows))
        mlflow.log_param("ocr_model", settings.ocr_model)
        mlflow.log_param("embedding_model", settings.embedding_model)

        for i, row in enumerate(target_rows):
            human_row_num = start_idx + i + 2  # +2 accounts for 1-based indexing and headers
            draft_id = row.get("Id borradores", "").strip() or f"row-{start_idx + i}"
            tracker.current_row_id = draft_id
            
            logger.info(f"\n[{i+1}/{len(target_rows)}] Row index: {start_idx + i} (CSV line {human_row_num}) | Draft ID: {draft_id}")
            
            # Use factory to parse the row into documents
            try:
                docs = SourceDocumentFactory.create_documents_from_csv_row(row)
            except Exception as e:
                logger.error(f"Failed to create documents from CSV row: {e}")
                processed_rows.append({
                    "row_index": start_idx + i,
                    "csv_line": human_row_num,
                    "draft_id": draft_id,
                    "documents": [],
                    "success": False,
                    "error": f"Row factory creation failed: {str(e)}"
                })
                continue

            row_docs_status = []
            for doc in docs:
                total_docs_count += 1
                doc_type_str = doc.document_type.value
                doc_filename = doc.filename
                logger.info(f" -> Processing document {doc.id} ({doc_type_str}) - Filename: {doc_filename}")
                
                doc_start = time.time()
                try:
                    # Select appropriate pipeline
                    selected_pipeline = pipeline_builder.build_pipeline_for_document(
                        document_type=doc.document_type,
                        document_repo=document_repo
                    )
                    
                    # Run the pipeline
                    ingest_command._run_pipeline(doc, pipeline=selected_pipeline)
                    doc_duration = time.time() - doc_start
                    
                    success_docs_count += 1
                    row_docs_status.append({
                        "doc_id": doc.id,
                        "filename": doc_filename,
                        "type": doc_type_str,
                        "status": "SUCCESS",
                        "latency_sec": doc_duration,
                        "error": None
                    })
                except Exception as exc:
                    doc_duration = time.time() - doc_start
                    failed_docs_count += 1
                    logger.error(f" -> Failed processing {doc.id}: {exc}")
                    row_docs_status.append({
                        "doc_id": doc.id,
                        "filename": doc_filename,
                        "type": doc_type_str,
                        "status": "FAILED",
                        "latency_sec": doc_duration,
                        "error": str(exc)
                    })

            processed_rows.append({
                "row_index": start_idx + i,
                "csv_line": human_row_num,
                "draft_id": draft_id,
                "documents": row_docs_status,
                "success": all(d["status"] == "SUCCESS" for d in row_docs_status) if row_docs_status else False,
                "error": None if all(d["status"] == "SUCCESS" for d in row_docs_status) else "Some documents failed"
            })

        total_duration = time.time() - start_time

        # Calculate final aggregated stats
        success_rate = (success_docs_count / total_docs_count * 100) if total_docs_count > 0 else 0.0
        
        # Log to MLflow
        mlflow.log_metric("total_duration_sec", total_duration)
        mlflow.log_metric("total_documents", total_docs_count)
        mlflow.log_metric("success_documents", success_docs_count)
        mlflow.log_metric("failed_documents", failed_docs_count)
        mlflow.log_metric("success_rate_pct", success_rate)
        
        mlflow.log_metric("ocr_calls", tracker.ocr_calls)
        mlflow.log_metric("ocr_input_tokens", tracker.ocr_input_tokens)
        mlflow.log_metric("ocr_output_tokens", tracker.ocr_output_tokens)
        mlflow.log_metric("ocr_total_time_sec", tracker.ocr_total_time)
        mlflow.log_metric("ocr_cost_usd", tracker.ocr_cost)
        
        mlflow.log_metric("embed_calls", tracker.embed_calls)
        mlflow.log_metric("embed_input_tokens", tracker.embed_input_tokens)
        mlflow.log_metric("embed_total_time_sec", tracker.embed_total_time)
        mlflow.log_metric("embed_cost_usd", tracker.embed_cost)
        
        mlflow.log_metric("total_cost_usd", tracker.total_cost)

        # Write detailed report to a markdown file
        write_markdown_report(
            start_idx=start_idx,
            end_idx=end_idx,
            total_duration=total_duration,
            total_docs_count=total_docs_count,
            success_docs_count=success_docs_count,
            failed_docs_count=failed_docs_count,
            success_rate=success_rate,
            processed_rows=processed_rows,
            tracker=tracker,
            run_id=run.info.run_id
        )

        print("\n" + "="*80)
        print("INGESTION METRICS SUMMARY")
        print("="*80)
        print(f"Total Rows Processed:      {len(target_rows)}")
        print(f"Total Documents:           {total_docs_count}")
        print(f"  - Successfully Ingested: {success_docs_count}")
        print(f"  - Failed:                {failed_docs_count}")
        print(f"Success Rate:              {success_rate:.2f}%")
        print(f"Total Duration:            {total_duration:.2f} seconds")
        print("-" * 40)
        print(f"Gemini OCR Calls:          {tracker.ocr_calls}")
        print(f"  - Input Tokens:          {tracker.ocr_input_tokens}")
        print(f"  - Output Tokens:         {tracker.ocr_output_tokens}")
        print(f"  - Total OCR Cost:        ${tracker.ocr_cost:.6f} USD")
        print(f"  - Total OCR Duration:    {tracker.ocr_total_time:.2f} seconds")
        print("-" * 40)
        print(f"Gemini Embeddings Calls:   {tracker.embed_calls}")
        print(f"  - Input Tokens:          {tracker.embed_input_tokens}")
        print(f"  - Total Embed Cost:      ${tracker.embed_cost:.6f} USD")
        print(f"  - Total Embed Duration:  {tracker.embed_total_time:.2f} seconds")
        print("-" * 40)
        print(f"TOTAL ESTIMATED COST:      ${tracker.total_cost:.6f} USD")
        print(f"MLflow Run ID:             {run.info.run_id}")
        print("="*80 + "\n")

def write_markdown_report(start_idx, end_idx, total_duration, total_docs_count, success_docs_count, failed_docs_count, success_rate, processed_rows, tracker, run_id):
    report_dir = Path(__file__).resolve().parent.parent.parent.parent / "artifacts"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "ingest_metrics_report.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Ingestion Pipeline Metrics Report (Rows {start_idx} to {end_idx})\n\n")
        f.write(f"This report summarizes the performance, token consumption, and API costs of the batch ingestion process run on **{time.strftime('%Y-%m-%d %H:%M:%S')}**.\n\n")
        
        f.write("## Execution Run Summary\n\n")
        f.write("| Metric | Value |\n")
        f.write("| --- | --- |\n")
        f.write(f"| **MLflow Run ID** | `{run_id}` |\n")
        f.write(f"| **CSV Row Range** | Indices {start_idx} to {end_idx} (1-based lines {start_idx+2} to {end_idx+2}) |\n")
        f.write(f"| **Total CSV Rows** | {end_idx - start_idx + 1} |\n")
        f.write(f"| **Total Documents Processed** | {total_docs_count} |\n")
        f.write(f"| **Successful Ingestions** | {success_docs_count} |\n")
        f.write(f"| **Failed Ingestions** | {failed_docs_count} |\n")
        f.write(f"| **Success Rate** | {success_rate:.2f}% |\n")
        f.write(f"| **Total Duration** | {total_duration:.2f} seconds (average {(total_duration/total_docs_count):.2f}s per doc) |\n")
        f.write(f"| **TOTAL ESTIMATED COST** | **${tracker.total_cost:.6f} USD** |\n\n")

        f.write("## API Usage & Cost Breakdown\n\n")
        f.write("| Service / Model | Calls | Input Tokens | Output Tokens | Total Latency | Cost (USD) |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        f.write(f"| **Gemini OCR (gemini-2.5-flash)** | {tracker.ocr_calls} | {tracker.ocr_input_tokens:,} | {tracker.ocr_output_tokens:,} | {tracker.ocr_total_time:.2f}s | ${tracker.ocr_cost:.6f} |\n")
        f.write(f"| **Gemini Embeddings (gemini-embedding-2)** | {tracker.embed_calls} | {tracker.embed_input_tokens:,} | 0 | {tracker.embed_total_time:.2f}s | ${tracker.embed_cost:.6f} |\n")
        f.write(f"| **TOTALS** | **{tracker.ocr_calls + tracker.embed_calls}** | **{tracker.ocr_input_tokens + tracker.embed_input_tokens:,}** | **{tracker.ocr_output_tokens:,}** | **{tracker.ocr_total_time + tracker.embed_total_time:.2f}s** | **${tracker.total_cost:.6f}** |\n\n")

        f.write("## Detailed Ingestion Log per CSV Row\n\n")
        f.write("| Row Idx | CSV Line | Draft ID | Document | Type | Status | Latency | Error |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        
        for row in processed_rows:
            row_idx = row["row_index"]
            csv_line = row["csv_line"]
            draft_id = row["draft_id"]
            docs = row["documents"]
            
            if not docs:
                f.write(f"| {row_idx} | {csv_line} | `{draft_id}` | N/A | N/A | FAILED | 0.0s | {row['error']} |\n")
            else:
                for idx_d, d in enumerate(docs):
                    # Only show row details once for rows with multiple documents
                    r_str = f"{row_idx}" if idx_d == 0 else ""
                    cl_str = f"{csv_line}" if idx_d == 0 else ""
                    d_str = f"`{draft_id}`" if idx_d == 0 else ""
                    
                    err_str = d["error"] if d["error"] else ""
                    f.write(f"| {r_str} | {cl_str} | {d_str} | {d['filename']} | {d['type']} | {d['status']} | {d['latency_sec']:.2f}s | {err_str} |\n")
        
        f.write("\n\n*Official pricing rates used:*\n")
        f.write("- *Gemini 2.5/3.5 Flash: Input $0.075 / 1M tokens, Output $0.30 / 1M tokens.*\n")
        f.write("- *Gemini Embedding 2: Input $0.025 / 1M tokens.*\n")
        
    logger.info(f"Detailed metrics report written to: {report_path}")

if __name__ == "__main__":
    run_metrics_ingest()
