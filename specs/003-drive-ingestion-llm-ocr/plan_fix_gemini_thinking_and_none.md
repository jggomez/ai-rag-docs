# Plan: Disable Thinking Budget & Enhance Extractor Robustness

To address the JSON truncation (`EOF while parsing a string`) and `NoneType` errors in the OCR ingestion pipeline under the `gemini-3-flash-preview` model, we will apply the following updates.

## Affected Files
* [gemini_extractor.py](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ingestion-pipeline/src/filters/gemini_extractor.py)

## Detailed Proposed Changes

### 1. Disable Thinking Budget & Increase Max Tokens
In `src/filters/gemini_extractor.py`, we will configure the `thinking_config` to disable thinking tokens (`thinking_budget=0`) during the OCR process and increase the `max_output_tokens` limit to `65536`. This saves latency/cost and guarantees enough output token budget for the JSON response.

```python
            # Use generate_content with response_schema for structured output
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=parts,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractedContent,
                    temperature=0.0,
                    max_output_tokens=65536,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=0
                    )
                ),
            )
```

### 2. Strengthen Extractor Robustness (Zero Trust Input Validation)
We will add defensive checks to ensure fields inside the response are validated before use:
* Check that `response.text` is not `None` before parsing.
* Fallback to manual parsing if `response.parsed` is `None` or has incomplete fields.
* Ensure `subject`, `body`, and `visual_tabular_data` are strings and not `None` before calling `.strip()`.

```python
            extracted_data: ExtractedContent = response.parsed
            
            # If parsed is None or missing crucial fields, fallback to manual validation
            if (extracted_data is None or 
                not hasattr(extracted_data, "subject") or 
                not hasattr(extracted_data, "body") or 
                not hasattr(extracted_data, "visual_tabular_data")):
                
                logger.warning("response.parsed is None or incomplete. Attempting manual parsing from response.text.")
                
                # Check for empty/blocked response
                text = response.text
                if not text:
                    finish_reason = "UNKNOWN"
                    if response.candidates and len(response.candidates) > 0:
                        finish_reason = response.candidates[0].finish_reason or "UNKNOWN"
                    raise ValueError(f"Gemini returned an empty/blocked response (finish reason: {finish_reason})")
                
                text = text.strip()
                if text.startswith("```"):
                    lines = text.splitlines()
                    if len(lines) >= 3:
                        text = "\n".join(lines[1:-1])
                try:
                    extracted_data = ExtractedContent.model_validate_json(text)
                except Exception as json_err:
                    finish_reason = "UNKNOWN"
                    if response.candidates and len(response.candidates) > 0:
                        finish_reason = response.candidates[0].finish_reason or "UNKNOWN"
                    logger.error(f"Failed to parse Gemini response as JSON. Finish reason: {finish_reason}. Text sample: {text[:200]}")
                    raise ValueError(f"Failed to parse Gemini response as JSON (finish reason: {finish_reason}): {json_err}")

            subject = getattr(extracted_data, "subject", "") or ""
            body = getattr(extracted_data, "body", "") or ""
            visual_data = getattr(extracted_data, "visual_tabular_data", "") or ""

            # Guard against empty body extraction
            if not isinstance(body, str) or not body.strip():
                logger.error(f"Gemini returned empty or invalid body for {payload.document.filename}")
                raise ValueError(f"OCR extraction returned empty body for {payload.document.filename}")

            # Merge visual/tabular data into body so it gets chunked and embedded
            full_text = body
            if isinstance(visual_data, str) and visual_data.strip():
                full_text += "\n\n---\n\n" + visual_data
```

## Verification Plan
1. Run local tests: `/Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ingestion-pipeline/.venv/bin/python -m pytest tests/unit/test_gemini_extractor.py` to ensure unit tests are green.
2. Restart the FastAPI server locally.
3. Rerun the 20-row ingestion script: `ingest_20_rows_api.py` and verify all files (including the 12MB files) ingest successfully without JSON truncation.
