# 🌎 Reporte de Estimación Global del Sistema: AI-RAG-Docs

Este reporte proporciona una visión integral de los costos operativos, requerimientos de infraestructura y métricas de rendimiento para el sistema completo de Gestión Documental con IA.

---

## 1. 📊 Resumen Ejecutivo de Costos (Mensual)
*Estimación proyectada para un entorno de **30 usuarios activos** con una carga de **1,800 documentos/mes** y **9,000 consultas RAG/mes**.*

| Servicio | Categoría | Descripción | Costo Est. (USD) |
| :--- | :--- | :--- | :--- |
| **Cloud Run** | Cómputo | 1 vCPU / 512MB RAM (4h/día actividad real) | **$6.05** |
| **Google Gemini API** | Inteligencia Artificial | OCR, Embeddings y Generación de Respuestas | **$17.45** |
| **Cloud Firestore** | Base de Datos | Almacenamiento NoSQL y Búsqueda Vectorial | **$1.70** |
| **Cloud Storage** | Almacenamiento | Repositorio de documentos originales (Nearline) | **$0.25** |
| **Networking** | Transferencia | Egress de datos y peticiones HTTP | **$0.16** |
| **TOTAL ESTIMADO** | | **Inversión Mensual Operativa** | **$25.61 USD** |

---

## 2. 🏗️ Arquitectura y Componentes del Sistema

### 🧠 Agente Conversacional y Pipeline (RAG)
Interfaz inteligente para consultas e ingesta de documentos.
*   **Recursos:** 1 vCPU / 512 MB RAM.
*   **Patrón de Carga:** 4 horas de ejecución real continua/día (120h/mes).
*   **Cálculo de Cómputo (Cloud Run):**
    *   **vCPU-s:** 432,000 consumidos - 180,000 (Capa Free) = 252,000 facturables → **$6.05 USD**.
    *   **GiB-s:** 216,000 consumidos - 360,000 (Capa Free) = 0 facturables → **$0.00 USD**.
*   **Tecnología:** OCR con Gemini 2.5 Flash + Firestore Vector Search + LLM.

### 💾 Almacenamiento de Conocimiento
*   **Firestore:** Indexación de ~20,000 chunks (proyectado para 1,000 docs base).
*   **Cloud Storage:** Bucket configurado en clase *Nearline* para optimizar costo/retención.

---

## 3. 📈 Métricas de Validación Reciente
*Resultados de la última prueba de estrés (Filas 100-200 del dataset maestro).*

| KPI | Valor |
| :--- | :--- |
| **Tasa de Éxito de Ingesta** | **96.26%** |
| **Precisión de Extracción (OCR)** | Lossless (Alta Fidelidad) |
| **Consumo de Tokens (Entrada)** | 361,018 tokens |
| **Consumo de Tokens (Salida)** | 139,475 tokens |
| **Latencia Máxima (Documento Grande)** | 88.02 segundos |

---

## 4. ⚙️ Configuraciones Recomendadas para Producción

1.  **Escalabilidad:** Mantener `max-instances: 10` para manejar picos de subida de documentos sin degradar el servicio.
2.  **Optimización de Costos:**
    *   **Cloud Scheduler:** Configurar el encendido de instancias a las 08:00 y apagado a las 18:00 (Ahorro de ~$140 USD vs 24/7).
    *   **Caché de Embeddings:** Implementar una capa de caché para documentos idénticos para evitar re-procesamiento.
3.  **Seguridad:** Uso de *Secret Manager* para `GEMINI_API_KEY` y credenciales de Cuentas de Servicio.

---
*Este reporte consolida la visión técnica y financiera del proyecto AI-RAG-Docs.*
