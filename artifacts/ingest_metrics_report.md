# 🌎 Reporte de Estimación Global del Sistema: AI-RAG-Docs

Este reporte proporciona una visión integral de los costos operativos, requerimientos de infraestructura y métricas de rendimiento para el sistema completo de Gestión Documental con IA.

---

## 1. 📊 Resumen Ejecutivo de Costos (Mensual)
*Estimación proyectada para un entorno de **30 usuarios activos** con una carga de **1,800 documentos/mes** y **9,000 consultas RAG/mes**.*

| Servicio | Categoría | Descripción | Costo Est. (USD) |
| :--- | :--- | :--- | :--- |
| **Cloud Run** | Cómputo | Instancias para Ingesta y Agente (Horario Laboral) | **$60.00** |
| **Google Gemini API** | Inteligencia Artificial | OCR, Embeddings y Generación de Respuestas | **$17.45** |
| **Cloud Firestore** | Base de Datos | Almacenamiento NoSQL y Búsqueda Vectorial | **$1.70** |
| **Cloud Storage** | Almacenamiento | Repositorio de documentos originales (Nearline) | **$0.25** |
| **Networking** | Transferencia | Egress de datos y peticiones HTTP | **$0.16** |
| **TOTAL ESTIMADO** | | **Inversión Mensual Operativa** | **$79.56 USD** |

---

## 2. 🏗️ Arquitectura y Componentes del Sistema

### 📥 Pipeline de Ingesta (Procesamiento)
Servicio encargado de la extracción y transformación de documentos.
*   **Capacidad:** Procesamiento de ~60 archivos diarios.
*   **Tecnología:** OCR con Gemini 2.5 Flash + Chunking semántico + Vectorización.
*   **Performance:** ~16 segundos por documento (media).
*   **Costo:** $0.00 (dentro de capa gratuita de cómputo).

### 🧠 Agente Conversacional (RAG)
Interfaz inteligente para consultas sobre la base de conocimiento.
*   **Capacidad:** ~300 consultas diarias de usuarios.
*   **Tecnología:** Recuperación de contexto (Firestore Vector Search) + LLM.
*   **Performance:** ~8 segundos de respuesta latencia final.
*   **Costo:** $0.00 (dentro de capa gratuita de cómputo).

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
