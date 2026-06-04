import logging
from typing import List, Dict, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

RESPONSE_GENERATION_PROMPT = """
<persona>
You are a senior technical communications writer specialized in engineering and
construction projects. You draft formal response letters on behalf of a project
supervision team.
</persona>

<task>
Draft a formal response letter to the received document described below.
Use the RAG context (similar past communications and previously sent response
letters) to match the established tone, structure, and level of technical detail.
</task>

<output_language>
You MUST write the entire response letter in **Spanish**. All text — greeting,
body, closing — must be in Spanish.
</output_language>

<received_document>
- **Subject**: {received_subject}
- **Content**: {received_body}
</received_document>

<project_metadata>
- **Contract**: {contract_number}
- **Original Sender**: {sender}
- **Work Front**: {work_front}
- **Document Date**: {document_date}
- **Process**: {process}
</project_metadata>

<rag_context>
## Similar Previously Received Communications
{similar_chunks_text}

## Style Reference — Previously Sent Response Letters
{sent_texts_block}
</rag_context>

<generation_rules>
1. Address the response to the original sender using a formal Spanish salutation.
2. Mirror the **tone, structure, and phrasing style** of the previously sent
   response letters provided as style reference. If no reference letters are
   available, use a standard formal engineering correspondence style.
3. Reference the contract number, work front, and any relevant technical details
   from the received document.
4. The response must be professional, concise, and action-oriented.
5. Use a clear structure: formal greeting → body addressing the subject → formal
   closing.
6. Do NOT include letterhead, logos, headers, or signature blocks — output ONLY
   the letter body text.
7. Do NOT fabricate technical data, dates, or commitments not supported by the
   provided context.
</generation_rules>
"""


class ResponseGenerator:
    """
    Generates a formal response letter text using Gemini LLM,
    combining triple RAG context: received document, similar chunks,
    and previously sent response documents.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        logger.info(f"ResponseGenerator initialized with model '{model_name}'.")

    def generate_response(
        self,
        received_subject: str,
        received_body: str,
        similar_chunks: List[dict],
        sent_texts: Dict[str, str],
        metadata: dict,
    ) -> str:
        """
        Generates a formal response text using Gemini with triple RAG context.

        Args:
            received_subject: Subject of the received document.
            received_body: Body text of the received document.
            similar_chunks: List of similar chunk dicts from vector search.
            sent_texts: Dict mapping draft_id to sent document text.
            metadata: Engineering metadata (contract, sender, work_front, etc.)

        Returns:
            Generated response text in Spanish.
        """
        # Format similar chunks as numbered context
        similar_chunks_text = self._format_similar_chunks(similar_chunks)

        # Format sent texts as reference block
        sent_texts_block = self._format_sent_texts(sent_texts)

        # Build the full prompt
        prompt = RESPONSE_GENERATION_PROMPT.format(
            received_subject=received_subject,
            received_body=received_body,
            contract_number=metadata.get("contract_number", "N/A"),
            sender=metadata.get("sender", "N/A"),
            work_front=metadata.get("work_front", "N/A"),
            document_date=metadata.get("document_date", "N/A"),
            process=metadata.get("process", "N/A"),
            similar_chunks_text=similar_chunks_text,
            sent_texts_block=sent_texts_block,
        )

        logger.info(f"Generating response with {len(similar_chunks)} chunks and {len(sent_texts)} sent texts.")

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=16384,
            ),
        )

        generated_text = response.text
        logger.info(f"Response generated successfully ({len(generated_text)} chars).")
        return generated_text

    def _format_similar_chunks(self, chunks: List[dict]) -> str:
        """Formats similar chunks into a numbered reference block."""
        if not chunks:
            return "No similar previous communications were found."

        lines = []
        for i, chunk in enumerate(chunks, 1):
            text = chunk.get("texto", "No text available")
            draft_id = chunk.get("id_borrador", "N/A")
            lines.append(f"### Similar Communication #{i} (Draft: {draft_id}):\n{text}\n")
        return "\n".join(lines)

    def _format_sent_texts(self, sent_texts: Dict[str, str]) -> str:
        """Formats sent document texts into a reference block."""
        if not sent_texts:
            return "No previous sent response letters were found for reference."

        lines = []
        for i, (draft_id, text) in enumerate(sent_texts.items(), 1):
            lines.append(f"### Sent Letter #{i} (Draft: {draft_id}):\n{text}\n")
        return "\n".join(lines)
