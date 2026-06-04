# Reporte de Métricas del Pipeline de Ingesta (Filas 100 a 200)

Este reporte resume el rendimiento, el consumo de tokens y los costos de la API del proceso de ingesta por lotes ejecutado el **2026-06-03 15:55:57**.

## Resumen de la Ejecución

| Métrica | Valor |
| --- | --- |
| **ID de Corrida de MLflow** | `1ca6a1e5896648df964750a7cb9ec596` |
| **Rango de Filas del CSV** | Índices 100 to 200 (líneas 1-basadas 102 to 202) |
| **Total de Filas del CSV** | 101 |
| **Total de Documentos Procesados** | 187 |
| **Ingestas Exitosas** | 180 |
| **Ingestas Fallidas** | 7 |
| **Tasa de Éxito** | 96.26% |
| **Duración Total** | 3002.97 segundos (promedio 16.06s por doc) |
| **COSTO TOTAL ESTIMADO** | **$0.058195 USD** |

## Desglose de Uso y Costos de la API

| Servicio / Modelo | Llamadas | Tokens de Entrada | Tokens de Salida | Latencia Total | Costo (USD) |
| --- | --- | --- | --- | --- | --- |
| **Gemini OCR (gemini-2.5-flash)** | 99 | 146,547 | 139,475 | 2189.46s | $0.052834 |
| **Gemini Embeddings (gemini-embedding-2)** | 726 | 214,471 | 0 | 548.50s | $0.005362 |
| **TOTALES** | **825** | **361,018** | **139,475** | **2737.96s** | **$0.058195** |


## Estimación de Volúmenes y Costos de Cloud Storage (Mensual - 30 días)

### 1. Estimación de Volúmenes (al mes)
* **Almacenamiento acumulado**: 60 archivos/día × 450 KB = 27,000 KB/día ≈ 27 MB al día. Al mes acumularías aproximadamente **810 MB** (menos de 1 GB).
* **Lecturas/Descargas (Egress/Retrieval)**: 100 archivos/día × 450 KB = 45,000 KB/día ≈ 45 MB al día. Al mes serían **1.35 GB** leídos.
* **Operaciones de Escritura (Clase A)**: 60 operaciones/día × 30 días = **1,800 operaciones/mes**.
* **Operaciones de Lectura (Clase B)**: 100 operaciones/día × 30 días = **3,000 operaciones/mes**.

### 2. Desglose de Costos (Tarifas estándar de Nearline en us-central1)
* **Costo por Almacenamiento (At-rest)**:
  * Tarifa: ~$0.011 USD por GB.
  * Cálculo: 0.81 GB × $0.011 = **$0.009 USD**.
* **Costo por Recuperación de Datos (Retrieval fee en Nearline)**:
  * Tarifa: $0.01 USD por GB al leer de Nearline.
  * Cálculo: 1.35 GB × $0.01 = **$0.013 USD**.
* **Costos de Operaciones (API Calls)**:
  * Clase A (Escritura): $0.01 USD por cada 1,000 ops. (1,800 ops = **$0.018 USD**).
  * Clase B (Lectura): $0.001 USD por cada 1,000 ops. (3,000 ops = **$0.003 USD**).
* **Red (Egress)**:
  * Depende del destino, pero si sale a Internet ronda los $0.12 USD por GB (1.35 GB ≈ **$0.16 USD**).
* **Costo Total Estimado**: **Menos de $0.25 USD al mes** (e incluso podría entrar en la capa gratuita (*Always Free*) si se cumplen ciertas condiciones de región).

---

## Estimación de Volúmenes y Costos de Firestore (Mensual)

### 1. Extrapolación de Métricas por Usuario

La estimación de actividad acumulada en un rango de tiempo para **1 usuario** promedio es:
* **Lecturas totales**: ~162 operaciones.
* **Escrituras totales**: 1,718 operaciones (354 en documentos principales y 279 en chunks, más los índices generados que Firestore cuenta internamente).

Asumiendo que esta carga representa la carga transaccional típica de **un día de uso activo** para un usuario interactuando con el agente RAG, las métricas base mensuales por usuario serían:
* **Lecturas/mes por usuario**: 162 ops × 30 días = **4,860 operaciones**.
* **Escrituras/mes por usuario**: 1,718 ops × 30 días = **51,540 operaciones**.

Para **30 usuarios activos al mes**:
* **Total Lecturas RAG**: 4,860 × 30 = **145,800 operaciones/mes**
* **Total Escrituras RAG**: 51,540 × 30 = **1,546,200 operaciones/mes**

---

### 2. Estimación de Almacenamiento (Base de Datos de Conocimiento)

Para una base de datos base con **1,000 documentos**:
* Cada documento tiene 20 propiedades.
* 2 propiedades de texto largo.
* 1 propiedad de embedding (un vector de 1536 dimensiones pesa aprox. **6 KB** solo el vector en formato numérico).
* **Tamaño promedio estimado por documento**: ~12 KB (incluyendo metadatos e indexación básica).
* **Almacenamiento total**: 1,000 docs × 12 KB = **12 MB**.

---

### 3. Desglose del Costo Mensual de Firestore (Precios estándar en us-central1)

Firestore ofrece una **Capa Gratuita (*Always Free*)** diaria que cubre una gran parte de este volumen:
* *Lecturas gratis*: 50,000 al día (1.5 Millones al mes).
* *Escrituras gratis*: 20,000 al día (600,000 al mes).
* *Almacenamiento gratis*: 1 GB al mes.

#### Aplicando la capa gratuita al consumo mensual estimado:

| Concepto | Consumo Mensual | Capa Gratuita Mensual | Excedente Facturable | Costo Unitario (Excedente) | Costo Estimado |
| --- | --- | --- | --- | --- | --- |
| **Almacenamiento** | 12 MB | 1 GB | 0 GB | $0.18 USD / GB | **$0.00 USD** |
| **Lecturas** | 145,800 ops | 1,500,000 ops | 0 ops | $0.06 USD / 100k ops | **$0.00 USD** |
| **Escrituras** | 1,546,200 ops | 600,000 ops | 946,200 ops | $0.18 USD / 100k ops | **$1.70 USD** |

> [!TIP]
> **Costo Total Estimado de Firestore**: **~$1.70 USD al mes**

---

### 💡 Notas importantes para el Agente RAG:
1. **Búsqueda Vectorial (Vector Search)**: Firestore soporta búsquedas de vecinos más cercanos (KNN) para embeddings. Si estás usando el índice vectorial integrado de Firestore para el RAG, ten en cuenta que las consultas vectoriales se cobran como **lecturas de documentos** basados en el número de documentos analizados/retornados. Dado tu bajo volumen de documentos (1,000), el impacto en costo seguirá estando dentro o muy cerca de la capa gratuita de lecturas.
2. **Crecimiento en Escrituras**: El costo principal actual viene de las escrituras de los `_chunks` de la base de datos. Si los 30 usuarios suben documentos constantemente, el costo escalará a razón de **$0.18 USD por cada 100,000 escrituras** ($1.80 USD por cada millón de escrituras) adicionales.

---

## Estimación de Costos de Cloud Run (Mensual - 30 Usuarios Activos)

La arquitectura está desacoplada en dos microservicios independientes que se escalan de forma separada según su patrón de carga.

> [!NOTE]
> **Región asumida**: Tier 1 (`us-central1`). Cloud Run cobra por segundo de ejecución real (CPU + Memoria). La **capa gratuita mensual** aplica globalmente a toda la cuenta:
> - **Peticiones gratuitas**: 2,000,000 / mes.
> - **vCPU-segundos gratuitos**: 180,000 / mes.
> - **GiB-segundos gratuitos**: 360,000 / mes.

---

### Servicio A: Pipeline de Ingesta de Documentos

Este servicio se activa solo cuando un usuario sube un archivo. Se asume una instancia de **2 vCPU / 4 GB RAM**.

**Supuestos de carga (basados en métricas reales de ingesta):**
- Archivos subidos: **60 archivos/día** entre todos los usuarios.
- Tiempo de procesamiento por archivo: **~16 segundos** (promedio medido).
- Peticiones totales al mes: 60 × 30 = **1,800 peticiones/mes**.
- Tiempo total de ejecución al mes: 1,800 × 16s = **28,800 segundos**.

**Consumo de recursos:**
| Recurso | Consumo Mensual | Capa Gratuita | Excedente | Tarifa (Excedente) | Costo |
| --- | --- | --- | --- | --- | --- |
| **Peticiones** | 1,800 | 2,000,000 | 0 | $0.40 / millón | **$0.00** |
| **vCPU-segundos** (2 vCPU × 28,800s) | 57,600 | 180,000 | 0 | $0.00002400 / vCPU-s | **$0.00** |
| **GiB-segundos** (4 GB × 28,800s) | 115,200 | 360,000 | 0 | $0.00000250 / GiB-s | **$0.00** |

> [!TIP]
> **Costo Estimado Servicio A (Ingesta)**: **$0.00 USD / mes** ✅ — Completamente dentro de la capa gratuita.

---

### Servicio B: Agente Conversacional (RAG)

Este servicio responde a las consultas de los usuarios. Se asume una instancia de **1 vCPU / 2 GB RAM**.

**Supuestos de carga (30 usuarios activos):**
- Consultas por usuario al día: ~10 preguntas.
- Total de consultas al mes: 10 × 30 usuarios × 30 días = **9,000 peticiones/mes**.
- Tiempo de respuesta promedio por consulta (RAG + LLM): **~8 segundos**.
- Tiempo total de ejecución al mes: 9,000 × 8s = **72,000 segundos**.

**Consumo de recursos:**
| Recurso | Consumo Mensual | Capa Gratuita | Excedente | Tarifa (Excedente) | Costo |
| --- | --- | --- | --- | --- | --- |
| **Peticiones** | 9,000 | 2,000,000 | 0 | $0.40 / millón | **$0.00** |
| **vCPU-segundos** (1 vCPU × 72,000s) | 72,000 | 180,000 | 0 | $0.00002400 / vCPU-s | **$0.00** |
| **GiB-segundos** (2 GB × 72,000s) | 144,000 | 360,000 | 0 | $0.00000250 / GiB-s | **$0.00** |

> [!TIP]
> **Costo Estimado Servicio B (Agente)**: **$0.00 USD / mes** ✅ — Completamente dentro de la capa gratuita.

---

### ⚠️ Factor Crítico: `min-instances` (Mitigación de Cold Start)

Si no se configura `min-instances`, Cloud Run escala a **cero instancias** cuando no hay tráfico. Esto puede generar latencias de arranque en frío (*cold start*) de **2 a 5 segundos** extra por petición.

Si se habilita `min-instances: 1` para cada servicio (para garantizar disponibilidad instantánea), la instancia se mantiene activa las 24 horas del día, generando el siguiente costo adicional:

| Servicio | Configuración | Segundos activos/mes | vCPU-s | GiB-s | Costo Adicional |
| --- | --- | --- | --- | --- | --- |
| **Ingesta** | 2 vCPU / 4 GB | 2,592,000 s | 5,184,000 | 10,368,000 | **~$135 USD** |
| **Agente** | 1 vCPU / 2 GB | 2,592,000 s | 2,592,000 | 5,184,000 | **~$67 USD** |

> [!WARNING]
> **Recomendación**: Para un equipo de 30 usuarios internos con horario laboral definido (8h/día, 5 días/semana), se recomienda usar `min-instances: 1` **solo en horario laboral** mediante un Cloud Scheduler que escale/desescale el servicio. Esto reduciría el costo de `min-instances` en **~70%**, de ~$202 USD a ~$60 USD/mes.

---

### Resumen Total Estimado de Cloud Run

| Escenario | Servicio A (Ingesta) | Servicio B (Agente) | **Total Mensual** |
| --- | --- | --- | --- |
| **Sin `min-instances`** (cold starts posibles) | $0.00 | $0.00 | **$0.00 USD** |
| **Con `min-instances: 1` (24/7)** | ~$135.00 | ~$67.00 | **~$202.00 USD** |
| **Con `min-instances: 1` (horario laboral)** | ~$40.00 | ~$20.00 | **~$60.00 USD** ✅ Recomendado |

---

## Resumen Consolidado de Costos Mensuales (30 Usuarios)

| Servicio | Costo Estimado / Mes |
| --- | --- |
| **Cloud Storage (Nearline)** | < $0.25 USD |
| **Firestore (Lecturas + Escrituras)** | ~$1.70 USD |
| **Cloud Run (horario laboral)** | ~$60.00 USD |
| **API Gemini (OCR + Embeddings)** | ~$17.45 USD* |
| **TOTAL ESTIMADO** | **~$79.40 USD / mes** |

> *Extrapolado desde el costo medido de $0.058 USD / 101 filas × 30,000 documentos proyectados al mes.

---

## Registro Detallado de Ingesta por Fila del CSV

| Índice Fila | Línea CSV | ID Borrador | Documento | Tipo | Estado | Latencia | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | 102 | `853467b9` | doc-853467b9 | ENVIADO | EXITOSO | 3.58s |  |
| 101 | 103 | `922f10f9` | CYS-CW276532-PHI-01740 | RECIBIDO | EXITOSO | 26.52s |  |
| 102 | 104 | `66fff8c8` | D-PHI-COP-0385-2025 | RECIBIDO | FALLIDO | 88.02s | 'NoneType' object has no attribute 'subject' |
| 103 | 105 | `99655cf4` | CYS-CW276532-PHI-01751 | RECIBIDO | EXITOSO | 33.19s |  |
|  |  |  | INT-OC-CYS-1326/25 | ENVIADO | EXITOSO | 4.41s |  |
| 104 | 106 | `8fa5db86` | CYS-CW276532-PHI-01762 | RECIBIDO | EXITOSO | 24.39s |  |
| 105 | 107 | `54cd500d` | CYS-CW276532-PHI-01773 | RECIBIDO | EXITOSO | 19.14s |  |
|  |  |  | INT-OC-CYS-1508/25 | ENVIADO | EXITOSO | 4.11s |  |
| 106 | 108 | `e92f6dac` | D-PHI-COP-0408-2025 | RECIBIDO | EXITOSO | 36.54s |  |
|  |  |  | INT-OC-CYS-1367/25 | ENVIADO | EXITOSO | 3.84s |  |
| 107 | 109 | `c12b5ade` | CYS-CW276532-PHI-01763 | RECIBIDO | EXITOSO | 31.64s |  |
|  |  |  | INT-OC-CYS-1539/25 | ENVIADO | EXITOSO | 3.63s |  |
| 108 | 110 | `f7385060` | CYS-CW276532-PHI-01779 | RECIBIDO | EXITOSO | 19.69s |  |
|  |  |  | INT-OC-CYS-1816/25 | ENVIADO | EXITOSO | 3.43s |  |
| 109 | 111 | `8af2e8a7` | CYS-CW276532-PHI-01785 | RECIBIDO | EXITOSO | 15.12s |  |
|  |  |  | INT-OC-CYS-1851/25 | ENVIADO | EXITOSO | 3.82s |  |
| 110 | 112 | `812050ba` | CYS-CW276532-PHI-01786 | RECIBIDO | EXITOSO | 13.13s |  |
|  |  |  | INT-OC-CYS-1548/25 | ENVIADO | EXITOSO | 3.90s |  |
| 111 | 113 | `c972fb36` | CYS-CW276532-PHI-01788 | RECIBIDO | EXITOSO | 17.53s |  |
|  |  |  | INT-OC-CYS-1430/25 | ENVIADO | EXITOSO | 3.87s |  |
| 112 | 114 | `6380a89d` | D-PHI-COP-0426-2025 | RECIBIDO | EXITOSO | 20.51s |  |
|  |  |  | INT-OC-CYS-1403/25 | ENVIADO | EXITOSO | 3.39s |  |
| 113 | 115 | `4f17a9b6` | CYS-CW276532-PHI-01791 | RECIBIDO | EXITOSO | 17.61s |  |
| 114 | 116 | `8d4d3491` | CYS-CW276532-PHI-01792 | RECIBIDO | EXITOSO | 24.14s |  |
|  |  |  | INT-OC-CYS-1648/25 | ENVIADO | EXITOSO | 3.38s |  |
| 115 | 117 | `0e92ece8` | D-PHI-COP-0428-2025 | RECIBIDO | EXITOSO | 22.41s |  |
|  |  |  | INT-OC-CYS-1397/25 | ENVIADO | EXITOSO | 3.85s |  |
| 116 | 118 | `ba697d5c` | D-PHI-COP-0430-2025 | RECIBIDO | EXITOSO | 19.25s |  |
|  |  |  | INT-OC-CYS-1396/25 | ENVIADO | EXITOSO | 79.38s |  |
| 117 | 119 | `bc9a5860` | CYS-CW276532-PHI-01802 | RECIBIDO | EXITOSO | 21.96s |  |
|  |  |  | INT-OC-CYS-1646/25 | ENVIADO | EXITOSO | 3.82s |  |
| 118 | 120 | `2076af00` | CYS-CW276532-PHI-01831 | RECIBIDO | EXITOSO | 36.13s |  |
|  |  |  | INT-OC-CYS-1727/25 | ENVIADO | EXITOSO | 3.69s |  |
| 119 | 121 | `574a1f37` | CYS-CW276532-PHI-01827 | RECIBIDO | EXITOSO | 18.45s |  |
|  |  |  | INT-OC-CYS-1720/25 | ENVIADO | EXITOSO | 3.71s |  |
| 120 | 122 | `cde5866a` | CYS-CW276532-PHI-01828 | RECIBIDO | EXITOSO | 18.69s |  |
|  |  |  | INT-OC-CYS-1718/25 | ENVIADO | EXITOSO | 4.34s |  |
| 121 | 123 | `01e09fcb` | CYS-CW276532-PHI-01829 | RECIBIDO | EXITOSO | 35.59s |  |
|  |  |  | INT-OC-CYS-1689/25 | ENVIADO | EXITOSO | 3.83s |  |
| 122 | 124 | `d84477da` | CYS-CW276532-PHI-01830 | RECIBIDO | EXITOSO | 15.20s |  |
|  |  |  | INT-OC-CYS-1729/25 | ENVIADO | EXITOSO | 3.61s |  |
| 123 | 125 | `4c1e083b` | CYS-CW276532-PHI-01835 | RECIBIDO | EXITOSO | 31.74s |  |
|  |  |  | INT-OC-CYS-1856/25 | ENVIADO | EXITOSO | 3.69s |  |
| 124 | 126 | `c8f76bf4` | CYS-CW276532-PHI-01837 | RECIBIDO | EXITOSO | 24.74s |  |
|  |  |  | INT-OC-CYS-2268/25 | ENVIADO | EXITOSO | 4.31s |  |
| 125 | 127 | `4f389c16` | CYS-CW276532-PHI-01852 | RECIBIDO | EXITOSO | 24.38s |  |
|  |  |  | INT-OC-CYS-1658/25 | ENVIADO | EXITOSO | 3.72s |  |
| 126 | 128 | `9d962feb` | CYS-CW276532-PHI-01847 | RECIBIDO | EXITOSO | 22.19s |  |
|  |  |  | INT-OC-CYS-1506/25 | ENVIADO | EXITOSO | 3.30s |  |
| 127 | 129 | `bda1e94c` | CYS-CW276532-PHI-01850 | RECIBIDO | EXITOSO | 26.21s |  |
|  |  |  | INT-OC-CYS-1649/25 | ENVIADO | EXITOSO | 3.37s |  |
| 128 | 130 | `b4a05a8d` | CYS-CW276532-PHI-01857 | RECIBIDO | EXITOSO | 75.00s |  |
|  |  |  | INT-OC-CYS-1823/25 | ENVIADO | FALLIDO | 1.86s | <HttpError 403 when requesting https://www.googleapis.com/drive/v3/files/1zYAOZQNvG8A20J3KO-x-iJVpTgwO9qw6?fields=name%2CmimeType%2Csize&alt=json returned "La solicitud tiene permisos insuficientes.". Details: "[{'message': 'Permiso Insuficiente', 'domain': 'global', 'reason': 'insufficientPermissions'}]"> |
| 129 | 131 | `7b26c732` | D-PHI-COP-0459-2025 | RECIBIDO | EXITOSO | 19.15s |  |
|  |  |  | INT-OC-CYS-1679/25 | ENVIADO | EXITOSO | 3.34s |  |
| 130 | 132 | `44b7545b` | D-PHI-COP-0465-2025 | RECIBIDO | EXITOSO | 26.23s |  |
|  |  |  | INT-OC-CYS-1515/25 | ENVIADO | EXITOSO | 3.88s |  |
| 131 | 133 | `9b7901b8` | CYS-CW276532-PHI-01874 | RECIBIDO | EXITOSO | 28.63s |  |
|  |  |  | INT-OC-CYS-1806/25 | ENVIADO | EXITOSO | 3.76s |  |
| 132 | 134 | `7e519eac` | D-PHI-CCE-ADM-1-C6751 | RECIBIDO | EXITOSO | 22.14s |  |
|  |  |  | INT-OC-CYS-1553/25 | ENVIADO | EXITOSO | 3.61s |  |
| 133 | 135 | `3ec6bc79` | D-PHI-COP-0474-2025 | RECIBIDO | EXITOSO | 20.84s |  |
|  |  |  | INT-OC-CYS-1565/25 | ENVIADO | EXITOSO | 3.29s |  |
| 134 | 136 | `d812a643` | CYS-CW276532-PHI-01894 | RECIBIDO | EXITOSO | 11.45s |  |
| 135 | 137 | `8ab364a3` | CYS-CW276532-PHI-01894 | RECIBIDO | EXITOSO | 11.27s |  |
|  |  |  | INT-OC-CYS-2376/25 | ENVIADO | EXITOSO | 3.42s |  |
| 136 | 138 | `93a8fe9f` | CYS-CW276532-PHI-01897 | RECIBIDO | EXITOSO | 49.44s |  |
|  |  |  | INT-OC-CYS-1744/25 | ENVIADO | EXITOSO | 4.87s |  |
| 137 | 139 | `1206289d` | CYS-CW276532-PHI-01902 | RECIBIDO | EXITOSO | 23.27s |  |
|  |  |  | INT-OC-CYS-2181/25 | ENVIADO | EXITOSO | 3.24s |  |
| 138 | 140 | `fd31df4f` | CYS-CW276532-PHI-01918 | RECIBIDO | EXITOSO | 25.96s |  |
|  |  |  | INT-OC-CYS-2264/25 | ENVIADO | EXITOSO | 3.36s |  |
| 139 | 141 | `b2b444c8` | CYS-CW276532-PHI-01922 | RECIBIDO | EXITOSO | 16.52s |  |
|  |  |  | INT-OC-CYS-1911/25 | ENVIADO | EXITOSO | 3.68s |  |
| 140 | 142 | `939cf5d6` | doc-939cf5d6 | ENVIADO | EXITOSO | 1.99s |  |
| 141 | 143 | `cb74d5db` | CYS-CW276532-PHI-01932 | RECIBIDO | FALLIDO | 71.59s | 'NoneType' object has no attribute 'subject' |
|  |  |  | INT-OC-CYS-1804/25 | ENVIADO | EXITOSO | 3.75s |  |
| 142 | 144 | `6e23aec6` | CYS-CW276532-PHI-01947 | RECIBIDO | EXITOSO | 37.63s |  |
|  |  |  | INT-OC-CYS-2117/25 | ENVIADO | EXITOSO | 5.41s |  |
| 143 | 145 | `4082fb93` | CYS-CW276532-PHI-01948 | RECIBIDO | EXITOSO | 28.32s |  |
|  |  |  | INT-OC-CYS-2431/25 | ENVIADO | EXITOSO | 4.85s |  |
| 144 | 146 | `219fa643` | CYS-CW276532-PHI-01951 | RECIBIDO | EXITOSO | 22.65s |  |
|  |  |  | INT-OC-CYS-1962/25 | ENVIADO | EXITOSO | 3.53s |  |
| 145 | 147 | `ff5b8567` | CYS-CW276532-PHI-01952 | RECIBIDO | EXITOSO | 21.09s |  |
|  |  |  | INT-OC-CYS-1978/25 | ENVIADO | EXITOSO | 3.28s |  |
| 146 | 148 | `356440b2` | CYS-CW276532-PHI-01953 | RECIBIDO | FALLIDO | 65.09s | 'NoneType' object has no attribute 'subject' |
|  |  |  | INT-OC-CYS-1981/25 | ENVIADO | EXITOSO | 3.09s |  |
| 147 | 149 | `7e8348a7` | CYS-CW276532-PHI-01954 | RECIBIDO | EXITOSO | 19.86s |  |
|  |  |  | INT-OC-CYS-1832/25 | ENVIADO | EXITOSO | 3.20s |  |
| 148 | 150 | `29f7e277` | CYS-CW276532-PHI-01955 | RECIBIDO | EXITOSO | 37.91s |  |
|  |  |  | INT-OC-CYS-2040/25 | ENVIADO | EXITOSO | 3.56s |  |
| 149 | 151 | `4158a769` | D-PHI-COP-0496-2025 | RECIBIDO | EXITOSO | 22.24s |  |
|  |  |  | INT-OC-CYS-1656/25 | ENVIADO | EXITOSO | 3.66s |  |
| 150 | 152 | `16321edc` | CYS-CW276532-PHI-01958 | RECIBIDO | EXITOSO | 39.77s |  |
|  |  |  | INT-OC-CYS-2180/25 | ENVIADO | EXITOSO | 3.70s |  |
| 151 | 153 | `6a4c2123` | CYS-CW276532-PHI-01960 | RECIBIDO | EXITOSO | 13.53s |  |
|  |  |  | INT-OC-CYS-2178/25 | ENVIADO | EXITOSO | 3.43s |  |
| 152 | 154 | `59483ac7` | CYS-CW276532-PHI-01977 | RECIBIDO | EXITOSO | 20.10s |  |
|  |  |  | INT-OC-CYS-1725/25 | ENVIADO | EXITOSO | 3.41s |  |
| 153 | 155 | `768ad656` | CYS-CW276532-PHI-01980 | RECIBIDO | EXITOSO | 22.94s |  |
|  |  |  | INT-OC-CYS-2116/25 | ENVIADO | EXITOSO | 4.77s |  |
| 154 | 156 | `189aaa8a` | D-PHI-COP-0501-2025 | RECIBIDO | EXITOSO | 17.55s |  |
|  |  |  | INT-OC-CYS-1715/25 | ENVIADO | EXITOSO | 5.21s |  |
| 155 | 157 | `eb714a3b` | CYS-CW276532-PHI-01989 | RECIBIDO | EXITOSO | 14.02s |  |
|  |  |  | INT-OC-CYS-1702/25 | ENVIADO | EXITOSO | 3.25s |  |
| 156 | 158 | `13623de0` | CYS-CW276532-PHI-01990 | RECIBIDO | EXITOSO | 18.53s |  |
|  |  |  | INT-OC-CYS-2379/25 | ENVIADO | EXITOSO | 4.88s |  |
| 157 | 159 | `bcb06ae3` | CYS-CW276532-PHI-02001 | RECIBIDO | EXITOSO | 13.03s |  |
|  |  |  | INT-OC-CYS-2184/25 | ENVIADO | EXITOSO | 3.33s |  |
| 158 | 160 | `16d74cbf` | CYS-CW276532-PHI-02011 | RECIBIDO | EXITOSO | 21.87s |  |
|  |  |  | INT-OC-CYS-1977/25 | ENVIADO | EXITOSO | 3.30s |  |
| 159 | 161 | `0ae2c3d5` | CYS-CW276532-PHI-02012 | RECIBIDO | EXITOSO | 15.10s |  |
|  |  |  | INT-OC-CYS-1985/25 | ENVIADO | EXITOSO | 3.77s |  |
| 160 | 162 | `7c13f88c` | D-PHI-COP-0516-2025 | RECIBIDO | EXITOSO | 17.88s |  |
| 161 | 163 | `1d841851` | CYS-CW276532-PHI-02025 | RECIBIDO | EXITOSO | 16.51s |  |
|  |  |  | INT-OC-CYS-2263/25 | ENVIADO | EXITOSO | 3.02s |  |
| 162 | 164 | `63edd595` | CYS-CW276532-PHI-02033 | RECIBIDO | EXITOSO | 24.69s |  |
|  |  |  | INT-OC-CYS-1850/25 | ENVIADO | EXITOSO | 3.45s |  |
| 163 | 165 | `eb0f9d73` | CYS-CW276532-PHI-02046 | RECIBIDO | FALLIDO | 66.49s | 'NoneType' object has no attribute 'subject' |
|  |  |  | INT-OC-CYS-2084/25 | ENVIADO | EXITOSO | 3.52s |  |
| 164 | 166 | `d28d1df8` | CYS-CW276532-PHI-02048 | RECIBIDO | EXITOSO | 67.06s |  |
|  |  |  | INT-OC-CYS-2177/25 | ENVIADO | EXITOSO | 3.62s |  |
| 165 | 167 | `510ac0e1` | D-PHI-COP-0523-2025 | RECIBIDO | FALLIDO | 73.68s | 'NoneType' object has no attribute 'subject' |
|  |  |  | INT-OC-CYS-1777/25 | ENVIADO | EXITOSO | 3.53s |  |
| 166 | 168 | `f432d87c` | CYS-CW276532-PHI-02068 | RECIBIDO | EXITOSO | 18.19s |  |
|  |  |  | INT-OC-CYS-2262/25 | ENVIADO | EXITOSO | 3.62s |  |
| 167 | 169 | `b952ca5b` | CYS-CW276532-PHI-02072 | RECIBIDO | EXITOSO | 17.76s |  |
|  |  |  | INT-OC-CYS-1828/25 | ENVIADO | EXITOSO | 3.19s |  |
| 168 | 170 | `fee44c60` | CYS-CW276532-PHI-02082 | RECIBIDO | EXITOSO | 20.26s |  |
|  |  |  | INT-OC-CYS-2598/25 | ENVIADO | EXITOSO | 3.66s |  |
| 169 | 171 | `bd8430a7` | CYS-CW276532-PHI-02084 | RECIBIDO | EXITOSO | 13.14s |  |
|  |  |  | INT-OC-CYS-2261/25 | ENVIADO | EXITOSO | 3.48s |  |
| 170 | 172 | `db0856ea` | CYS-CW276532-PHI-02088 | RECIBIDO | FALLIDO | 68.04s | 'NoneType' object has no attribute 'subject' |
|  |  |  | INT-OC-CYS-2430/25 | ENVIADO | EXITOSO | 3.58s |  |
| 171 | 173 | `706f1863` | CYS-CW276532-PHI-02090 | RECIBIDO | EXITOSO | 16.74s |  |
|  |  |  | INT-OC-CYS-1854/25 | ENVIADO | EXITOSO | 3.38s |  |
| 172 | 174 | `1e3b9832` | CYS-CW276532-PHI-02096 | RECIBIDO | EXITOSO | 18.81s |  |
|  |  |  | INT-OC-CYS-2545/25 | ENVIADO | EXITOSO | 3.30s |  |
| 173 | 175 | `b23813e2` | D-PHI-COP-0533-2025 | RECIBIDO | EXITOSO | 16.80s |  |
|  |  |  | INT-OC-CYS-1841/25 | ENVIADO | EXITOSO | 3.70s |  |
| 174 | 176 | `7aba785c` | CYS-CW276532-PHI-02114 | RECIBIDO | EXITOSO | 17.71s |  |
|  |  |  | INT-OC-CYS-2354/25 | ENVIADO | EXITOSO | 3.27s |  |
| 175 | 177 | `222e6e63` | CYS-CW276532-PHI-02126 | RECIBIDO | EXITOSO | 20.61s |  |
| 176 | 178 | `a36bf2f7` | CYS-CW276532-PHI-02142 | RECIBIDO | EXITOSO | 25.78s |  |
| 177 | 179 | `5336b55d` | CYS-CW276532-PHI-02148 | RECIBIDO | EXITOSO | 18.27s |  |
| 178 | 180 | `767a80f0` | CYS-CW276532-PHI-02166 | RECIBIDO | EXITOSO | 15.86s |  |
|  |  |  | INT-OC-CYS-2021/25 | ENVIADO | EXITOSO | 3.48s |  |
| 179 | 181 | `46020406` | D-PHI-COP-0561-2025 | RECIBIDO | EXITOSO | 13.25s |  |
|  |  |  | INT-OC-CYS-1949/25 | ENVIADO | EXITOSO | 5.36s |  |
| 180 | 182 | `26701d8f` | CYS-CW276532-PHI-02169 | RECIBIDO | EXITOSO | 12.08s |  |
|  |  |  | INT-OC-CYS-1980/25 | ENVIADO | EXITOSO | 3.19s |  |
| 181 | 183 | `3d8e4bb6` | D-PHI-COP-0564-2025 | RECIBIDO | EXITOSO | 20.09s |  |
|  |  |  | INT-OC-CYS-1952/25 | ENVIADO | EXITOSO | 3.05s |  |
| 182 | 184 | `b48d6018` | CYS-CW276532-PHI-02174 | RECIBIDO | EXITOSO | 24.35s |  |
|  |  |  | INT-OC-CYS-2083/25 | ENVIADO | EXITOSO | 3.20s |  |
| 183 | 185 | `9ca41bc1` | D-PHI-COP-0577-2025 | RECIBIDO | EXITOSO | 21.43s |  |
| 184 | 186 | `9c91a7f0` | CYS-CW276532-PHI-02212 | RECIBIDO | EXITOSO | 26.64s |  |
|  |  |  | INT-OC-CYS-2703/25 | ENVIADO | EXITOSO | 4.55s |  |
| 185 | 187 | `212ac608` | CYS-CW276532-PHI-02213 | RECIBIDO | EXITOSO | 25.41s |  |
|  |  |  | INT-OC-CYS-2757/25 | ENVIADO | EXITOSO | 4.07s |  |
| 186 | 188 | `1c69a831` | CYS-CW276532-PHI-02219 | RECIBIDO | EXITOSO | 14.48s |  |
| 187 | 189 | `d5f69c2f` | D-PHI-COP-0592-2025 | RECIBIDO | EXITOSO | 16.71s |  |
|  |  |  | INT-OC-CYS-2092/25 | ENVIADO | EXITOSO | 3.66s |  |
| 188 | 190 | `9bbd8ab7` | CYS-CW276532-PHI-02221 | RECIBIDO | EXITOSO | 11.14s |  |
|  |  |  | INT-OC-CYS-2260/25 | ENVIADO | EXITOSO | 3.37s |  |
| 189 | 191 | `33cf8302` | CYS-CW276532-PHI-02222 | RECIBIDO | EXITOSO | 15.90s |  |
|  |  |  | INT-OC-CYS-2318/25 | ENVIADO | EXITOSO | 3.49s |  |
| 190 | 192 | `86cc42f1` | D-PHI-COP-0594-2025 | RECIBIDO | EXITOSO | 34.95s |  |
| 191 | 193 | `27c6d040` | CYS-CW276532-PHI-02230 | RECIBIDO | EXITOSO | 31.37s |  |
|  |  |  | INT-OC-CYS-2585/25 | ENVIADO | EXITOSO | 3.67s |  |
| 192 | 194 | `c16aa93d` | D-PHI-COP-0598-2025 | RECIBIDO | EXITOSO | 41.01s |  |
|  |  |  | INT-OC-CYS-2119/25 | ENVIADO | EXITOSO | 3.60s |  |
| 193 | 195 | `15fd5b5b` | D-PHI-COP-0605-2025 | RECIBIDO | EXITOSO | 26.38s |  |
|  |  |  | INT-OC-CYS-2165/25 | ENVIADO | EXITOSO | 4.31s |  |
| 194 | 196 | `58286048` | CYS-CW276532-PHI-02256 | RECIBIDO | EXITOSO | 18.89s |  |
|  |  |  | INT-OC-CYS-2723/25 | ENVIADO | EXITOSO | 3.41s |  |
| 195 | 197 | `b9af5c68` | CYS-CW276532-PHI-02277 | RECIBIDO | EXITOSO | 18.84s |  |
|  |  |  | INT-OC-CYS-2228/25 | ENVIADO | EXITOSO | 3.97s |  |
| 196 | 198 | `3320e75d` | CYS-CW276532-PHI-02284 | RECIBIDO | EXITOSO | 14.68s |  |
|  |  |  | INT-OC-CYS-2220/25 | ENVIADO | EXITOSO | 3.51s |  |
| 197 | 199 | `57c9d925` | CYS-CW276532-PHI-02290 | RECIBIDO | EXITOSO | 25.76s |  |
|  |  |  | INT-OC-CYS-2583/25 | ENVIADO | EXITOSO | 3.71s |  |
| 198 | 200 | `87ee96bf` | CYS-CW276532-PHI-02293 | RECIBIDO | EXITOSO | 34.07s |  |
|  |  |  | INT-OC-CYS-2364/25 | ENVIADO | EXITOSO | 4.15s |  |
| 199 | 201 | `c19d8d63` | D-PHI-COP-0620-2025 | RECIBIDO | EXITOSO | 19.97s |  |
|  |  |  | INT-OC-CYS-2204/25 | ENVIADO | EXITOSO | 3.53s |  |
| 200 | 202 | `ecc3322a` | D-PHI-COP-0621-2025 | RECIBIDO | EXITOSO | 24.51s |  |


*Tarifas oficiales utilizadas:*
- *Gemini 2.5/3.5 Flash: Entrada $0.075 / 1M tokens, Salida $0.30 / 1M tokens.*
- *Gemini Embedding 2: Entrada $0.025 / 1M tokens.*