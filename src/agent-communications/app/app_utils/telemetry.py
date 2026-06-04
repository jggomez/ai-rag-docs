# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import mlflow
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


def setup_telemetry() -> str | None:
    """Configure OpenTelemetry and MLflow tracing based on official ADK integration docs."""

    # 1. Prevent MLflow from overriding the ADK/OTEL provider
    os.environ["MLFLOW_USE_DEFAULT_TRACER_PROVIDER"] = "false"
    
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5001")
    experiment_name = "agent-communications"
    
    try:
        # 2. Configure MLflow Tracking
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        exp = mlflow.get_experiment_by_name(experiment_name)
        
        if exp:
            # 3. Configure the OpenTelemetry tracer provider for MLflow OTLP ingestion
            # Endpoint is the MLflow server's OTLP traces path
            otlp_endpoint = f"{tracking_uri.rstrip('/')}/v1/traces"
            
            # Required env vars for some SDKs, but we set it manually below too
            os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = otlp_endpoint
            os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"x-mlflow-experiment-id={exp.experiment_id}"

            exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                headers={"x-mlflow-experiment-id": exp.experiment_id}
            )
            
            tracer_provider = TracerProvider()
            tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
            trace.set_tracer_provider(tracer_provider)
            
            # 4. Enable automatic tracing for Google GenAI SDK (Gemini)
            mlflow.gemini.autolog()
            
            logging.info(f"MLflow & ADK OTLP tracing enabled at {otlp_endpoint} [Exp ID: {exp.experiment_id}]")

    except Exception as e:
        logging.warning(f"Could not initialize MLflow/OTLP telemetry: {e}")

    # ADK/GCS Telemetry (Optional logging to bucket)
    bucket = os.environ.get("LOGS_BUCKET_NAME")
    capture_content = os.environ.get(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
    )
    if bucket and capture_content != "false":
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "NO_CONTENT"
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload")
        os.environ.setdefault(
            "OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental"
        )
        commit_sha = os.environ.get("COMMIT_SHA", "dev")
        os.environ.setdefault(
            "OTEL_RESOURCE_ATTRIBUTES",
            f"service.namespace=agent-documents,service.version={commit_sha}",
        )
        path = os.environ.get("GENAI_TELEMETRY_PATH", "completions")
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
            f"gs://{bucket}/{path}",
        )

    return bucket
