# Proyecto AI-RAG-DOCS: Reglas de Identificación y Vinculación

Este documento establece las verdades fundamentales sobre cómo se identifican y relacionan las comunicaciones recibidas y enviadas en el sistema. **Estas reglas deben respetarse en cada nueva sesión del agente.**

## 1. Claves de Identificación (Metadata)

Cada fila del CSV representa una interacción que genera hasta dos documentos en Firestore: uno en `docs-recibidos` y otro en `docs-enviados`.

| Campo Firestore | Propósito | Origen CSV (Recibidos) | Origen CSV (Enviados) |
| :--- | :--- | :--- | :--- |
| `id_borrador` | **Vínculo Técnico.** Clave de unión entre colecciones. | Columna `Id borradores` | Columna `Id borradores` |
| `nombre_objeto` | **Identidad de Usuario.** Código oficial buscable. | `cod_document` (vía `codigo_comunicado` metadata) | `cod_document` (vía `codigo_comunicado` metadata) |
| `nombre_archivo` | Nombre del archivo físico real. | Extraído de la descarga de `url_doc`. | Extraído de la descarga de `url_doc`. |

## 2. Reglas para el Agente (AI Agent)

Para garantizar la trazabilidad total, el Agente debe seguir estas directrices:

*   **Identificación Única:** El campo `nombre_objeto` es la verdad absoluta para el código oficial del documento que el usuario ingresa en la UI (`cod_document`).
*   **Búsqueda:** Cuando el usuario proporciona un código (ej. "CYS-xxx"), el agente debe buscar en el campo `nombre_objeto` de Firestore.
*   **Vinculación (Cruzado):** Para encontrar la respuesta a una carta recibida (o viceversa), el agente **DEBE** usar el campo `id_borrador`.
    *   *Ejemplo:* Si encuentra un chunk en `docs-recibidos` con `id_borrador: "123"`, debe buscar en `docs-enviados` el documento con `id_borrador: "123"` para obtener el texto de la respuesta.
*   **Presentación al Usuario:** El agente debe referirse a los documentos por su `nombre_objeto`.
    *   *Formato Sugerido:* "Encontré la carta recibida **[nombre_objeto_REC]** y su respuesta enviada fue la **[nombre_objeto_SEN]**."

## 3. Reglas de Ingesta (Pipeline)

*   La factoría de documentos (`factory.py`) es la encargada de mapear `codigo_comunicado` -> `nombre_objeto`.
*   Para documentos `SENT`, nunca se debe sobreescribir el `nombre_objeto` con el código de recibidos; cada uno mantiene su propia identidad de columna del CSV.

---
*Última actualización: 08 de Junio, 2026*
