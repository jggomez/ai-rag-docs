# Feature Specification: UI Menu Options for Ingestion, Retrieval, and Chat Agent

**Feature Branch**: `006-ui-menu-options`  
**Created**: 2026-06-06  
**Status**: Draft  
**Input**: User description: "en la UI vamos a crear tres opciones en el menu, 1 es que el usuario envie un doc de recibido y este llama ingestdocumentreceived api se le pide al usuaio en un formulario la data, y suba el archivo llamando a la api de upload, luego llamar al ingestdocumentreceived, 2. la opcion de colocar el codcomunicadorecibido, iddocumentrecibido para obtener el doc de enviado cread en el proceso del raG osea la api de retrieve. 3 opcion la del agente"

## Clarifications

### Session 2026-06-06
- Q: Should the UI display the generated response text in addition to the PDF download link in the Retrieve view? → A: Display only the PDF download link and metadata (subject, chunk counts). No response text is shown on screen.
- Q: What validation and format should the UI apply to document_date in the Ingestion Form? → A: Standard HTML5 Date picker formatting to YYYY-MM-DD, sending "UNKNOWN" if empty.
- Q: What are the retrieve fields and how should they be named and handled in RAG retrieval? → A: The fields are `received_communication_code`, `received_document_id`, `start_date`, `end_date`, and `front`. All fields must be in English and use snake_case python format. The RAG system must filter by `front` (Firestore pre-filter) and dates (`start_date` and `end_date` as Firestore pre-filters based on the document date field `fecha_documento`) first. These fields are optional.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Option Navigation Menu (Priority: P1)

As a user, I want a sidebar or navigation header menu with three distinct options (Ingest Received Document, RAG Document Retrieval, Chat Agent), so that I can easily navigate between the different parts of the application.

**Why this priority**: Essential to build the shell layout and enable switching between different functionalities.

**Independent Test**: Load the app, verify that the menu displays all three options, and click each to ensure the displayed view updates correctly.

**Acceptance Scenarios**:

1. **Given** the UI is loaded, **When** the side/header menu is displayed, **Then** three options are visible: "Ingesta", "Búsqueda RAG", and "Chat de Agente".
2. **Given** the user clicks "Ingesta", **When** the navigation completes, **Then** the Ingestion Form view is displayed.
3. **Given** the user clicks "Búsqueda RAG", **When** the navigation completes, **Then** the RAG Retrieval view is displayed.
4. **Given** the user clicks "Chat de Agente", **When** the navigation completes, **Then** the conversational Chat Agent view is displayed.

---

### User Story 2 - Upload and Ingest Received Document (Priority: P1)

As a user, I want a form to enter metadata and select a PDF file, so that the document is uploaded to GCS and successfully ingested into the RAG system.

**Why this priority**: Primary ingestion workflow allowing user-driven document registration.

**Independent Test**: Fill out the metadata fields, upload a sample PDF, click submit, and verify that the file is uploaded to GCS via `/api/v1/upload` and ingested via `/api/v1/ingestdocumentreceived`.

**Acceptance Scenarios**:

1. **Given** the user is on the Ingest Received Document page, **When** they fill out the form fields (`work_front`, `document_date`, `id_borrador`, `filename`, `document_type="received"`, `url_doc`) and select a PDF file, **Then** clicking submit:
   - Uploads the PDF file to GCS via `/api/v1/upload`.
   - Obtains the public GCS URL.
   - Invokes `/api/v1/ingestdocumentreceived` using the flat payload structure.
   - Renders a success notification showing the created document ID (e.g. `76857089_REC`).
2. **Given** the user is on the Ingest Received Document page, **When** they submit the form without selecting a file or leaving required fields blank, **Then** the UI shows validation errors and prevents the submission.

---

### User Story 3 - RAG Retrieval with ID/Code (Priority: P1)

As a user, I want to retrieve generated response documents by entering a document code or ID, so that I can download and review RAG-generated replies.

**Why this priority**: Core retrieval interface allowing access to generated PDF drafts.

**Independent Test**: Enter a known document code or ID, click "Retrieve", and verify that the app calls `POST /api/v1/retrieve` and displays the generated PDF link.

**Acceptance Scenarios**:

1. **Given** a document with code `"REC-001"` is already ingested, **When** the user enters `"REC-001"` in the `received_communication_code` field and clicks retrieve, **Then** the UI calls `POST /api/v1/retrieve` using English snake_case payload parameters, and renders the returned metadata and clickable download link to the PDF.
2. **Given** a user is on the retrieval view, **When** they fill out `received_communication_code`, `front`, `start_date`, and `end_date`, **Then** the UI submits these fields to the backend, which filters RAG results by front and date range first before generating the response.
3. **Given** a user is on the retrieval view, **When** they click retrieve with both identifier fields (`received_communication_code` and `received_document_id`) empty, **Then** the UI shows a validation message warning that at least one identifier must be provided.

---

### User Story 4 - Conversational Chat Agent View (Priority: P1)

As a user, I want to switch to the Chat Agent view, so that I can converse with the ADK agent as before.

**Why this priority**: Preserves the existing interactive chat system capability.

**Independent Test**: Switch to the Chat Agent view, type a query, and verify that the agent responds.

**Acceptance Scenarios**:

1. **Given** the user is on the Chat Agent page, **When** they submit a message, **Then** the app calls `/run` and displays the agent's reply.

---

### Edge Cases

- **Upload Network Failure**: If the `/api/v1/upload` call fails, the UI must intercept the error, display a friendly warning, and prevent calling `/api/v1/ingestdocumentreceived`.
- **API Timeout**: If the RAG retrieval takes longer than expected, the UI must show a loading spinner and allow the user to cancel or wait.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The UI MUST implement a sidebar or navigation header with three items: "Ingesta de Documento", "Búsqueda y RAG", and "Chat de Agente".
- **FR-002**: The Ingestion view MUST render a form containing the following input fields:
  - `work_front` (Text Input, required)
  - `document_date` (HTML5 Date Input, formats to YYYY-MM-DD, optional, defaults to "UNKNOWN" if left blank)
  - `id_borrador` (Text Input, required)
  - `filename` (Text Input, required, defaults to selected file name)
  - `document_type` (Select dropdown: "received" or "sent", required)
  - File Upload component (accepting only `.pdf`, required)
- **FR-003**: Upon Ingestion form submission, the UI MUST first call `POST /api/v1/upload` with the file data, then call `POST /api/v1/ingestdocumentreceived` with the flat request body mapping the returned GCS URL as `url_doc`.
- **FR-004**: The Retrieve view MUST render a form containing:
  - `received_communication_code` (Text Input, optional)
  - `received_document_id` (Text Input, optional)
  - `start_date` (HTML5 Date Input, optional)
  - `end_date` (HTML5 Date Input, optional)
  - `front` (Text Input, optional)
- **FR-005**: Upon Retrieve submission, the UI MUST call `POST /api/v1/retrieve` with the flat payload using English snake_case parameters. On success, it MUST render the returned subject, similar chunk count, sent document count, and a clickable PDF download link (converting `gs://` to `https://storage.googleapis.com/`). The raw generated response text is not displayed on screen.
- **FR-007**: The retrieve API endpoint (`POST /api/v1/retrieve`) MUST accept `received_communication_code`, `received_document_id`, `start_date`, `end_date`, and `front` as optional parameters in a JSON payload.
- **FR-008**: The retrieval process (`RetrieveAndGenerateCommand` and `FirestoreVectorSearchRepository`) MUST pre-filter search candidates in Firestore by both `front` (mapped to `frente_trabajo` in Firestore) and the date range (`start_date` and `end_date` mapped to chunk `fecha_documento` in Firestore) first, before executing the vector search query, reranking, and returning context chunks for downstream text/PDF generation. If `front` is provided, it takes precedence over the fetched document's work front.
- **FR-006**: The Agent Chat view MUST embed the existing chat interface, preserving user session IDs.

### Key Entities

- **UI View State**: Manages which of the three views ("ingestion", "retrieve", "agent") is currently active.
- **Upload File Payload**: Contains the raw PDF binary data uploaded to the server.
- **Flat Ingestion Payload**: Maps flat metadata fields and `url_doc` to the backend.
- **Flat Retrieval Payload**: Contains `codcomunicadorecibido` and `iddocumentrecibido` fields.

## Design & Performance Standards *(mandatory)*

- **UX Consistency**: The new navigation and forms must match the design styling, fonts, and dark/light mode of the existing chat interface.
- **Latency**: Switching between menu views must be instantaneous (<50ms).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Clicking menu links changes the view instantly without reloading the page.
- **SC-002**: Documents uploaded and ingested through the UI form are successfully saved in Firestore, and the resulting ID is displayed to the user.
- **SC-003**: Searching by code or ID calls the retrieval API and renders the generated response text and PDF download link.

## Assumptions

- The backend service at `http://localhost:8080` is running and accessible from the browser.
- Standard session-based or route-based state management is sufficient for switching views.
