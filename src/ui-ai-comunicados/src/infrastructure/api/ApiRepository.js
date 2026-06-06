/**
 * ApiRepository - Central HTTP client for backend communication.
 *
 * Connects to two backends:
 *   - Ingestion Pipeline (upload, ingest, retrieve)
 *   - Agent Communications (ADK agent queries via /run)
 */

const INGESTION_BASE_URL = window.config?.VITE_INGESTION_API_URL || 'http://localhost:8080';
const AGENT_BASE_URL = window.config?.VITE_AGENT_API_URL || 'http://localhost:8000';

/**
 * Helper to convert gs:// URL to public storage URL
 * @param {string} gcsUrl
 * @returns {string}
 */
export function formatGcsUrl(gcsUrl) {
  if (!gcsUrl || !gcsUrl.startsWith('gs://')) return gcsUrl;
  return gcsUrl.replace('gs://', 'https://storage.googleapis.com/');
}

/**
 * Upload a PDF file to GCS via the ingestion pipeline.
 * @param {File} file - The File object from the input element.
 * @returns {Promise<{status: string, gcs_url: string, filename: string}>}
 */
export async function uploadFileToGCS(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${INGESTION_BASE_URL}/api/v1/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Upload failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Trigger the RAG retrieve-and-generate pipeline for a received document.
 * @param {object} params
 * @param {string} params.gcsUrl      - The gs:// URL returned by uploadFileToGCS.
 * @param {string} params.filename    - Original filename.
 * @param {object} params.metadata    - Form metadata fields.
 * @returns {Promise<{status: string, subject: string, similar_count: number, sent_count: number, gcs_url: string}>}
 */
export async function retrieveDocument({ gcsUrl, filename, metadata }) {
  const payload = {
    url: gcsUrl,
    document_type: 'received',
    filename: filename,
    metadata: {
      sender: metadata.sender || '',
      contract_number: metadata.contractNumber || '',
      work_front: metadata.workFront || '',
      document_date: metadata.documentDate || '',
      process: metadata.process || '',
    },
  };

  const response = await fetch(`${INGESTION_BASE_URL}/api/v1/retrieve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Retrieve failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Ingest a received document with flat metadata.
 * @param {object} params
 * @param {string} params.workFront
 * @param {string} params.documentDate
 * @param {string} params.idBorrador
 * @param {string} params.filename
 * @param {string} params.documentType
 * @param {string} params.urlDoc
 * @returns {Promise<{status: string, document_id: string, filename: string, document_type: string}>}
 */
export async function ingestReceivedDocument({
  workFront,
  documentDate,
  idBorrador,
  filename,
  documentType,
  urlDoc,
}) {
  const payload = {
    work_front: workFront,
    document_date: documentDate || 'UNKNOWN',
    id_borrador: idBorrador,
    filename: filename,
    document_type: documentType,
    url_doc: urlDoc,
  };

  const response = await fetch(`${INGESTION_BASE_URL}/api/v1/ingestdocumentreceived`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Ingestion failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Trigger RAG retrieve-and-generate search with optional front/date pre-filtering.
 * @param {object} params
 * @param {string} [params.receivedCommunicationCode]
 * @param {string} [params.receivedDocumentId]
 * @param {string} [params.startDate]
 * @param {string} [params.endDate]
 * @param {string} [params.front]
 * @returns {Promise<{status: string, subject: string, similar_count: number, sent_count: number, gcs_url: string}>}
 */
export async function searchAndRetrieveDocument({
  receivedCommunicationCode,
  receivedDocumentId,
  startDate,
  endDate,
  front,
}) {
  const payload = {
    received_communication_code: receivedCommunicationCode || null,
    received_document_id: receivedDocumentId || null,
    start_date: startDate || null,
    end_date: endDate || null,
    front: front || null,
  };

  const response = await fetch(`${INGESTION_BASE_URL}/api/v1/retrieve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Retrieval failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Send a user message to the ADK agent and return the assistant response text.
 *
 * Each chat mount generates a fresh sessionId (UUID) so the agent always
 * starts with a clean conversation history. The sessionId must be provided
 * by the caller — there is no default to prevent accidental session reuse.
 *
 * @param {string} userMessage - The user's question.
 * @param {string} sessionId   - Unique session ID for this conversation (UUID).
 * @returns {Promise<string>} The agent's text response.
 */
export async function queryAgent(userMessage, sessionId) {
  const appName = 'app';
  const userId = 'ui-user';

  const sessionUrl = `${AGENT_BASE_URL}/apps/${appName}/users/${userId}/sessions/${sessionId}`;

  try {
    const sessionResponse = await fetch(sessionUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ origen: 'frontend-web', inicializado: true }),
    });

    // 409 = session already exists, which is fine (idempotent)
    if (!sessionResponse.ok && sessionResponse.status !== 409) {
      console.warn(`Session creation returned: ${sessionResponse.status}`);
    }
  } catch (sessionError) {
    console.error('Error creating session:', sessionError);
  }

  const payload = {
    appName: appName,
    userId: userId,
    sessionId: sessionId,
    newMessage: {
      role: 'user',
      parts: [{ text: userMessage }],
    },
    streaming: false,
  };

  const response = await fetch(`${AGENT_BASE_URL}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Agent query failed with status ${response.status}`);
  }

  const responseData = await response.json();

  if (Array.isArray(responseData)) {
    for (let i = responseData.length - 1; i >= 0; i--) {
      const content = responseData[i]?.content;
      if (content?.role === 'model') {
        const textParts = (content.parts || [])
          .filter(part => part && typeof part === 'object' && 'text' in part)
          .map(part => part.text);

        if (textParts.length > 0) {
          return textParts.join('\n');
        }
      }
    }
  }

  return 'No response received from agent.';
}