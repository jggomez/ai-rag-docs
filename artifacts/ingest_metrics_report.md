# 📊 Reporte Consolidado: Pipeline de Ingesta RAG

Este documento presenta el análisis de rendimiento, volúmenes de datos y la proyección de costos operativos para el sistema de ingesta de documentos técnicos.

---

## 1. 📈 Resumen de Ejecución (Muestra de Control)
*Datos obtenidos de la corrida de validación sobre 101 filas del CSV.*

| Métrica | Resultado |
| :--- | :--- |
| **ID Corrida (MLflow)** | `1ca6a1e5896648df964750a7cb9ec596` |
| **Documentos Procesados** | 187 |
| **Tasa de Éxito** | **96.26%** (180 exitosos, 7 fallidos) |
| **Tiempo Total** | 50.05 minutos |
| **Promedio por Documento** | 16.06 segundos |

---

## 2. 💰 Estimación de Costos Operativos (Mensual)
*Proyección basada en un equipo de **30 usuarios activos**.*

### A. Servicios de Infraestructura (Google Cloud)
| Servicio | Escenario / Configuración | Costo Est. (USD) |
| :--- | :--- | :--- |
| **Cloud Run** | Horario laboral (8h/día, min-instances: 1) | **$60.00** |
| **Firestore** | 1.5M escrituras/mes (Excedente Capa Free) | **$1.70** |
| **Cloud Storage** | Almacenamiento Nearline (< 1GB) | **$0.25** |
| **Red (Egress)** | Transferencia de datos a Internet | **$0.16** |
| **Subtotal Infraestructura** | | **$62.11** |

### B. Inteligencia Artificial (Google Gemini API)
| Componente | Uso Estimado | Costo Est. (USD) |
| :--- | :--- | :--- |
| **LLM OCR (Flash 2.5)** | Transcripción de documentos | **$16.00** |
| **Embeddings (v2)** | Vectorización para búsqueda | **$1.45** |
| **Subtotal IA** | | **$17.45** |

> [!IMPORTANT]
> **TOTAL MENSUAL ESTIMADO: ~$79.56 USD**
> *Ahorro potencial de **$202 USD** si se evitan `min-instances` 24/7.*

---

## 3. 📂 Desglose por Unidad de Servicio

### 🧠 Servicio de Agente (RAG)
*   **Recursos:** 1 vCPU / 2 GB RAM.
*   **Carga:** 9,000 consultas/mes (300/día).
*   **Performance:** ~8s de respuesta promedio.
*   **Costo:** $0.00 (Capa gratuita) + Proporción de `min-instances`.

### 📥 Pipeline de Ingesta
*   **Recursos:** 2 vCPU / 4 GB RAM.
*   **Carga:** 1,800 archivos/mes (60/día).
*   **Performance:** ~16s por archivo (OCR + Chunking + Embedding).
*   **Costo:** $0.00 (Capa gratuita) + Proporción de `min-instances`.

---

## 4. 📝 Registro Detallado de Ingesta (Fragmento)

| Línea CSV | ID Borrador | Documento | Estado | Latencia | Error / Observación |
| :---: | :--- | :--- | :---: | :---: | :--- |
| 102 | `853467b9` | doc-853467b9 | ✅ | 3.58s | - |
| 103 | `922f10f9` | CYS-CW276532-PHI-01740 | ✅ | 26.52s | - |
| 104 | `66fff8c8` | D-PHI-COP-0385-2025 | ❌ | 88.02s | NoneType error in extractor |
| 105 | `99655cf4` | CYS-CW276532-PHI-01751 | ✅ | 33.19s | - |
| 118 | `ba697d5c` | D-PHI-COP-0430-2025 | ✅ | 79.38s | Latencia alta por tamaño PDF |
| 130 | `b4a05a8d` | CYS-CW276532-PHI-01857 | ❌ | 1.86s | Permisos insuficientes (Drive) |

---

## 5. 💡 Recomendaciones de Optimización
1.  **Gestión de Instancias:** Implementar Cloud Scheduler para apagar `min-instances` fuera de horario de oficina.
2.  **Manejo de Errores:** Investigar los fallos tipo `NoneType` en el extractor para mejorar la tasa de éxito (actualmente 96%).
3.  **Drive Auth:** Revisar permisos de la cuenta de servicio para los documentos que arrojaron error 403.

---
*Reporte generado automáticamente por Gemini CLI.*
