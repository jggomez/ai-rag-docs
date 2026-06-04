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
        texts = [f"{chunk.subject}\n{chunk.body}" for chunk in payload.chunks]
        
        import concurrent.futures
        import time
        import random
        
        def get_single_embedding(text: str) -> list[float]:
            max_retries = 5
            base_delay = 1.0
            for attempt in range(max_retries):
                try:
                    result = self.client.models.embed_content(
                        model=self.model,
                        contents=text,
                        config=types.EmbedContentConfig(
                            task_type="RETRIEVAL_DOCUMENT",
                            output_dimensionality=768
                        )
                    )
                    if not result.embeddings or len(result.embeddings) == 0:
                        raise ValueError("No embeddings returned from Gemini API")
                    return result.embeddings[0].values
                except Exception as e:
                    is_rate_limit = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
                    if is_rate_limit and attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                        logger.warning(f"Rate limited (429) during embedding. Retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})...")
                        time.sleep(delay)
                    else:
                        raise e
            raise ValueError("Failed to generate embedding after retries")

        try:
            # Generate embeddings concurrently using a thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                embeddings_values = list(executor.map(get_single_embedding, texts))
                
            # Assign generated embeddings back to the chunks
            for i, values in enumerate(embeddings_values):
                payload.chunks[i].embedding = values
                
            logger.info("Successfully generated all embeddings concurrently using Google GenAI SDK.")
            return payload

        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise e
