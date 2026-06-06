# Servicio de Pipeline de Ingesta (Ingestion Pipeline)

El Servicio de Pipeline de Ingesta es un flujo asíncrono y de alto rendimiento diseñado para procesar documentos técnicos y correspondencia de ingeniería. Opera bajo una arquitectura limpia de Tuberías y Filtros (Pipe and Filter), aplicando estrategias de extracción condicional dependiendo de la clasificación de origen de cada documento.

---

## Características Principales

* **Restricción de Columnas CSV (7 Columnas)**:
  * El pipeline de ingesta masiva (`/api/v1/ingest/batch`) procesa estrictamente las **7 columnas principales** del archivo `Comunicaciones.csv`, ignorando cualquier columna adicional:
    1. `Id borradores` (Mapeado como `draft_id`)
    2. `Fecha` (Mapeado como `document_date`)
    3. `Frente` (Mapeado como `work_front`)
    4. `Recibidas` (Nombre del archivo recibido)
    5. `url Recibidas` (URL de Google Drive del archivo recibido)
    6. `Enviadas` (Nombre del archivo enviado/respuesta)
    7. `Ubicacion filtradas` (URL de Google Drive del archivo enviado)
* **Valores Predeterminados (Fallbacks)**:
  * Si faltan campos mandatorios en una fila del CSV, el pipeline aplica valores por defecto automáticamente:
    * `draft_id` (Id borradores): Si está vacío, se autogenera un Hash MD5 único a partir del contenido de la fila.
    * `document_date` (Fecha): Si está vacío, se establece por defecto como `"UNKNOWN"`.
    * `work_front` (Frente): Si está vacío, se establece por defecto como `"GENERAL"`.
* **Procesamiento Independiente y Regla de Omisión (Skip Rule)**:
  * Las columnas de recibidos (`url Recibidas`) y enviados (`Ubicacion filtradas`) en una misma fila se procesan de forma **completamente independiente**.
  * Si la URL de un documento contiene `"Sin ruta"`, `"Sin URL origen"` o es `"UNKNOWN"`, **no se realiza ningún procesamiento** para ese documento (se salta la descarga de Google Drive, no se crea el registro en Firestore, no se generan fragmentos de texto ni se guarda en la base de datos).
  * Si una fila tiene una URL válida en Recibidos y una URL inválida (o `"Sin ruta"`) en Enviados, se ingesta y se guarda únicamente el documento recibido en la base de datos de recibidos, saltándose por completo el documento enviado (y viceversa).
* **Arquitectura de Ingesta Híbrida**:
  * **Documentos Enviados (SENT)**: Extraídos mediante lectura estructural de PDF en local usando expresiones regulares especializadas (`PDFReader` + `DocumentCleaner`).
  * **Documentos Recibidos (RECEIVED)**: Extraídos mediante OCR impulsado por LLM utilizando `gemini-2.5-flash` con instrucciones de diseño visual para preservar tablas y maquetación (`GeminiExtractor`).

---

## Configuración

Para ejecutar la aplicación localmente o dentro de un contenedor, duplique la plantilla de configuración y defina las variables requeridas:

```bash
cp .env.example .env
```

### Variables de Entorno

| Variable | Tipo | Descripción | Requerido |
|---|---|---|---|
| `GCP_PROJECT_ID` | String | Identificador del proyecto de Google Cloud | Sí |
| `GCP_REGION` | String | Región de despliegue de Cloud Run | Sí |
| `GCS_INGESTION_BUCKET`| String | Bucket de GCS destino para eventos de ingesta | Sí |
| `GCS_INGESTION_PREFIX`| String | Prefijo de subdirectorio en GCS | Sí |
| `FIRESTORE_DATABASE` | String | Base de datos de Firestore por defecto (inicializada como `(default)`) | No |
| `GEMINI_API_KEY` | String | API Key de Google Gemini para llamadas al modelo de IA | Sí |
| `EMBEDDING_MODEL` | String | Modelo para generación de vectores (por defecto: `gemini-embedding-2`) | No |
| `OCR_MODEL` | String | Modelo de LLM para OCR visual (por defecto: `gemini-2.5-flash`) | No |
| `LOG_LEVEL` | String | Nivel de severidad del Logger de Python (`DEBUG`, `INFO`, `ERROR`) | No |
| `FIRESTORE_DATABASE_RECEIVED`| String | Base de datos de Firestore destino para Recibidos (`docs-recibidos`) | Sí |
| `FIRESTORE_DATABASE_SENT`| String | Base de datos de Firestore destino para Enviados (`docs-enviados`) | Sí |

---

## Arquitectura Técnica

El flujo de ingesta se desacopla en filtros aislados que comparten estado mediante un `ProcessingPayload`. El pipeline enruta y bifurca la estrategia según el tipo de documento:

```mermaid
flowchart TD
    %% Entradas
    subgraph Entrada ["Interfaces de Entrada / API"]
        API_Single["POST /api/v1/ingest<br>(Ingesta Individual)"]
        API_Batch["POST /api/v1/ingest/batch<br>(Ingesta Masiva CSV)"]
        Eventarc["GCS Eventarc Trigger<br>(Cloud Storage Events)"]
    end

    %% Componente Central / Casos de Uso
    subgraph Orquestacion ["Capa de Aplicación y Casos de Uso"]
        Cmd["IngestDocumentCommand<br>(Orquestador de Ingesta)"]
        Builder["PipelineBuilder<br>(Constructor de Tuberías)"]
    end

    %% Tubería de Procesamiento
    subgraph Pipeline ["Pipeline de Procesamiento (Pipe & Filter)"]
        Downloader["1. DriveDownloader<br>(Descarga GCS / Drive API)"]
        
        %% Ramificaciones
        Bifurcador{"¿Tipo de Documento?"}
        
        subgraph SentBranch ["Rama de Enviados (SENT)"]
            Reader["2a. PDFReader<br>(Extracción de Texto PDF)"]
            Cleaner["3a. DocumentCleaner<br>(Limpieza y OCR Fix)"]
        end
        
        subgraph RecBranch ["Rama de Recibidos (RECEIVED)"]
            Extractor["2b. GeminiExtractor<br>(Gemini 2.5 LLM OCR)"]
        end
        
        %% Etapas Comunes
        Chunker["4. TextChunker<br>(Segmentación Semántica)"]
        Embedder["5. VectorEmbedder<br>(Vectores de Embedding Gemini)"]
        Saver["6. VectorSaver<br>(Preparación de Modelos)"]
    end

    %% Persistencia
    subgraph DB ["Capa de Persistencia (Firestore)"]
        RoutingRepo["RoutingFirestoreDocumentRepository"]
        DB_Rec["Firestore docs-recibidos<br>(Colecciones: documentos, documentos_chunks)"]
        DB_Sen["Firestore docs-enviados<br>(Colecciones: documentos, documentos_chunks)"]
    end

    %% Flujos de datos y control
    API_Single --> Cmd
    API_Batch --> Cmd
    Eventarc --> Cmd
    Cmd --> Builder
    Builder --> Pipeline
    
    Downloader --> Bifurcador
    Bifurcador -->|Enviado| Reader
    Reader --> Cleaner
    Cleaner --> Chunker
    
    Bifurcador -->|Recibido| Extractor
    Extractor --> Chunker
    
    Chunker --> Embedder
    Embedder --> Saver
    Saver --> RoutingRepo
    
    RoutingRepo -->|Filtro ID / Tipo| DB_Rec
    RoutingRepo -->|Filtro ID / Tipo| DB_Sen

    %% Estilos Visuales
    style Bifurcador fill:#f9f,stroke:#333,stroke-width:2px
    style DB_Rec fill:#bbf,stroke:#333,stroke-width:1px
    style DB_Sen fill:#bbf,stroke:#333,stroke-width:1px
```

---

## Documentación de API (Endpoints)

El servicio está expuesto mediante FastAPI:

### GET `/health`
Verifica la disponibilidad y salud del servicio.
* **Respuesta**: `{"status": "ok"}`

### POST `/api/v1/ingest`
Ejecuta la ingesta síncrona y enrutamiento dual de un solo documento a partir de una URL y metadatos explícitos.
* **Cuerpo de la Petición (Payload)**:
  ```json
  {
    "url": "https://drive.google.com/file/d/.../view",
    "document_type": "received",
    "metadata": {
      "sender": "CYS",
      "contract_number": "CW 12345",
      "work_front": "Descarga",
      "document_date": "26/02/2025",
      "process": "Supervisión",
      "response_file_url": "https://drive.google.com/file/d/.../view"
    }
  }
  ```
* **Respuesta**: `{"status": "completed", "document_id": "...", "filename": "...", "document_type": "received"}`

### POST `/api/v1/ingest/batch`
Inicia el procesamiento masivo de todas las filas registradas en el archivo CSV local configurado en las propiedades (`METADATA_CSV_PATH`).
* **Respuesta**:
  ```json
  {
    "status": "completed",
    "processed_records": 6,
    "total_records": 6
  }
  ```

### POST `/api/v1/ingestdocumentreceived`
Realiza la ingesta individual de un documento recibido o enviado utilizando una estructura de payload plana (sin objetos anidados).
* **Cuerpo de la Petición (Payload)**:
  ```json
  {
    "work_front": "Descarga",
    "document_date": "2026-06-06",
    "id_borrador": "76857089",
    "filename": "REC-001.pdf",
    "document_type": "received",
    "url_doc": "https://drive.google.com/file/d/.../view"
  }
  ```
* **Respuesta**:
  ```json
  {
    "status": "completed",
    "received_document": {
      "document_id": "76857089_REC",
      "filename": "REC-001.pdf",
      "document_type": "received"
    },
    "sent_document": null
  }
  ```

### POST `/api/v1/retrieve`
Endpoint del recuperador RAG. Recibe el código de comunicado recibido (`codcomunicadorecibido`) y/o el identificador único de Firestore del documento (`iddocumentrecibido`). Recupera el contenido textual directamente desde Firestore para realizar la búsqueda semántica híbrida, la resolución de correspondencias y la generación de la respuesta en PDF sin volver a realizar descargas de Drive ni OCR.
* **Cuerpo de la Petición (Payload)**:
  ```json
  {
    "codcomunicadorecibido": "REC-001",
    "iddocumentrecibido": "doc-id-123"
  }
  ```
  *(Nota: Se requiere proveer al menos uno de los dos parámetros)*
* **Respuesta**:
  ```json
  {
    "status": "completed",
    "subject": "Asunto del Documento",
    "similar_count": 5,
    "sent_count": 2,
    "gcs_url": "gs://..."
  }
  ```

---

## Ejecución de Pruebas y Cobertura

### ⚠️ Evitar Bloqueos de Conexión de MLflow
El servicio incluye autologging y trazabilidad de LLMs integrado con MLflow. Para evitar que las pruebas se queden colgadas esperando la conexión de red de un servidor remoto de MLflow (timeout HTTP), el entorno define `ENABLE_MLFLOW=false` en los archivos `.env` de pruebas. También se incluye una verificación de salud resiliente de 1 segundo para evitar esperas y reintentos innecesarios.

### Script de Pruebas Unificado (`run_tests.sh`)
Para facilitar la ejecución de pruebas locales de manera rápida e interactiva, se han diseñado scripts automatizados:

* **Pruebas Rápidas (Unitarias y Funcionales)**:
  Ejecuta solo la suite rápida (omitiendo llamadas reales a GCP Firestore y Gemini):
  ```bash
  # Desde la raíz del proyecto
  ./run_tests.sh
  ```
* **Pruebas Completas de Integración (`--all` / `-a`)**:
  Ejecuta la suite completa de integración, solicitando interactivamente el ID del proyecto de GCP para conectar a las bases de datos reales en Firestore:
  ```bash
  # Desde la raíz del proyecto
  ./run_tests.sh --all
  ```

### Reporte de Cobertura Completo (85% Cobertura Total)
Para medir la cobertura de código en las pruebas unitarias y de integración del pipeline:

```bash
# Desde la raíz
cd src/ingestion-pipeline
export RUN_FIRESTORE_TESTS="true"
.venv/bin/python -m pytest tests/ --cov=src
```

Esto generará el reporte de cobertura en terminal, confirmando los siguientes niveles de cobertura en los módulos críticos:
* `cleaner.py`: **100% Cobertura**
* `pdf_generator.py`: **98% Cobertura**
* `drive_downloader.py`: **97% Cobertura**
* `csv_metadata_repository.py`: **96% Cobertura**
* `embedder.py`: **96% Cobertura**
* `document_repo.py`: **86% Cobertura** (con aserciones corregidas para tipo de documento y metadatos unificados)
* `vector_search_repo.py`: **86% Cobertura**
* `retrieve_and_generate.py`: **88% Cobertura**
