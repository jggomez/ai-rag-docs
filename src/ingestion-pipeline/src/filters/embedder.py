import logging
from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.filters.base import Filter
from src.domain.entities import ProcessingPayload

logger = logging.getLogger(__name__)

class VectorEmbedder(Filter[ProcessingPayload, ProcessingPayload]):
    def __init__(self, api_key: str, model: str = "models/embedding-001"):
        """
        Initializes the embedder with Google Generative AI.
        Default model is set to embedding-001 (Gemini).
        """
        self.embeddings = GoogleGenerativeAIEmbeddings(
            google_api_key=api_key,
            model=model
        )

    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        if not payload.chunks:
            logger.warning("No chunks found to embed.")
            return payload
            
        logger.info(f"Generating embeddings for {len(payload.chunks)} chunks (Subject + Body).")
        
        # Combine subject and body for a richer semantic vector
        texts = [f"Subject: {chunk.subject}\nBody: {chunk.body}" for chunk in payload.chunks]
        
        try:
            vectors = self.embeddings.embed_documents(texts)
            
            for i, vector in enumerate(vectors):
                payload.chunks[i].embedding = vector
                
            logger.info("Successfully generated all embeddings.")
            return payload

        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise e
