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

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env relative to the script directory to support running from any directory
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# IMPORT AND INITIALIZE TELEMETRY FIRST - BEFORE ANY ADK OR GOOGLE IMPORTS
from app.app_utils.telemetry import setup_telemetry
setup_telemetry()

from app.app_utils.typing import Feedback
from google.cloud import logging as google_cloud_logging
from google.adk.cli.fast_api import get_fast_api_app
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi import FastAPI
import google.auth
import traceback

_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
allow_origins_str = os.environ.get("ALLOW_ORIGINS", "*")
if allow_origins_str == "*":
    allow_origins = ["*"]
    allow_credentials = False
else:
    allow_origins = [origin.strip() for origin in allow_origins_str.split(",") if origin.strip()]
    allow_credentials = True

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# In-memory session configuration - no persistent storage
session_service_uri = None

artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

# 2. Initialize ADK App. 
# We set otel_to_cloud=False because we are managing the TracerProvider manually in setup_telemetry()
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    otel_to_cloud=False, 
)
app.title = "agent-communications"
app.description = "API for interacting with the Agent agent-documents"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        print("!!! Agent Exception !!!", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error en el agente.",
                "exception": str(e),
                "traceback": traceback.format_exc()
            },
            headers={"Access-Control-Allow-Origin": "*"}
        )


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
