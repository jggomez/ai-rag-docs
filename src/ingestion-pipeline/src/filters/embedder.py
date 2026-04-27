import logging
from google import genai
from google.genai import types
from src.filters.base import Filter
from src.domain.entities import ProcessingPayload

logger = logging.getLogger(__name__)

class VectorEmbedder(Filter[ProcessingPayload, ProcessingPayload]):
    def __init__(self, api_key: str, model: str = "gemini-embedding-2"):
        """
        Initializes the embedder with Google GenAI SDK.
        Default model is set to text-embedding-004.
        """
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        if not payload.chunks:
            logger.warning("No chunks found to embed.")
            return payload
            
        logger.info(f"Generating embeddings for {len(payload.chunks)} chunks using {self.model}.")
        
        # Combine subject and body for a richer semantic vector
        texts = [f"Subject: {chunk.subject}\nBody: {chunk.body}" for chunk in payload.chunks]
        
        try:
            # Generate embeddings using the new SDK
            result = self.client.models.embed_content(
                model=self.model,
                contents=texts,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            
            if not result.embeddings:
                raise ValueError("No embeddings returned from Gemini API")

            # result.embeddings is a list of Embedding objects (each has a .values attribute)
            for i, emb in enumerate(result.embeddings):
                payload.chunks[i].embedding = emb.values
                
            logger.info("Successfully generated all embeddings using Google GenAI SDK.")
            return payload

        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise e
