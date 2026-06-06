import { uploadFileToGCS, ingestReceivedDocument } from '../infrastructure/api/ApiRepository.js';

/**
 * Execute the upload-and-ingest workflow.
 * @param {File} file - The PDF file from the input element.
 * @param {object} metadata - Form field values.
 * @returns {Promise<{uploadResult: object, ingestResult: object}>}
 */
export async function executeUploadDocument(file, metadata) {
  // Step 1: Upload file to GCS
  const uploadResult = await uploadFileToGCS(file);

  // Step 2: Trigger the metadata ingestion pipeline
  const ingestResult = await ingestReceivedDocument({
    workFront: metadata.workFront,
    documentDate: metadata.documentDate,
    idBorrador: metadata.idBorrador,
    filename: uploadResult.filename,
    documentType: metadata.documentType || 'received',
    urlDoc: uploadResult.gcs_url,
  });

  return { uploadResult, ingestResult };
}
