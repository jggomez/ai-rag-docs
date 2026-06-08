import { uploadFileToGCS, ingestReceivedDocument, ingestSentDocument } from '../infrastructure/api/ApiRepository.js';

/**
 * Execute the upload-and-ingest workflow.
 * @param {File} file - The PDF file from the input element.
 * @param {object} metadata - Form field values.
 * @returns {Promise<{uploadResult: object, ingestResult: object}>}
 */
export async function executeUploadDocument(file, metadata) {
  const documentType = metadata.documentType || 'received';

  // Step 1: Upload file to GCS with date and type for folder organization
  const uploadResult = await uploadFileToGCS(file, metadata.documentDate, documentType);

  // Step 2: Select the correct ingestion method
  const ingestMethod = documentType === 'sent' ? ingestSentDocument : ingestReceivedDocument;

  // Step 3: Trigger the metadata ingestion pipeline
  const ingestResult = await ingestMethod({
    workFront: metadata.workFront,
    documentDate: metadata.documentDate,
    idBorrador: metadata.idBorrador,
    codDocument: metadata.codDocument,
    documentType: documentType,
    urlDoc: uploadResult.gcs_url,
  });

  return { uploadResult, ingestResult };
}
