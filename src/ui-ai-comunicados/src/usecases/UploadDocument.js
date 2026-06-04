/**
 * UploadDocument Use Case
 *
 * Orchestrates:
 * 1. Upload PDF to GCS via /api/v1/upload
 * 2. Trigger RAG retrieve-and-generate via /api/v1/retrieve
 */
import { uploadFileToGCS, retrieveDocument } from '../infrastructure/api/ApiRepository.js';

/**
 * Execute the upload-and-retrieve workflow.
 * @param {File} file - The PDF file from the input element.
 * @param {object} metadata - Form field values.
 * @returns {Promise<{uploadResult: object, retrieveResult: object}>}
 */
export async function executeUploadDocument(file, metadata) {
  // Step 1: Upload file to GCS
  const uploadResult = await uploadFileToGCS(file);

  // Step 2: Trigger the RAG retrieval pipeline with the GCS URL
  const retrieveResult = await retrieveDocument({
    gcsUrl: uploadResult.gcs_url,
    filename: uploadResult.filename,
    metadata: metadata,
  });

  return { uploadResult, retrieveResult };
}
