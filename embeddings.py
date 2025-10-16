"""Embedding generation using Google Gemini."""
import logging
from typing import Optional

import google.generativeai as genai
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

from config import settings

logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=settings.google_api_key)


class EmbeddingGenerator:
    """Generate embeddings using Gemini embedding model."""

    def __init__(self, model_name: str = None):
        """Initialize embedding generator."""
        self.model_name = model_name or settings.gemini_embedding_model
        logger.info(f"Initialized embedding generator with model: {self.model_name}")

    @retry(
        wait=wait_random_exponential(min=settings.retry_min_wait, max=settings.retry_max_wait),
        stop=stop_after_attempt(settings.max_retry_attempts),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate embedding for text."""
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None

        try:
            # Gemini embedding API call
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document",
            )

            embedding = result["embedding"]
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    @retry(
        wait=wait_random_exponential(min=settings.retry_min_wait, max=settings.retry_max_wait),
        stop=stop_after_attempt(settings.max_retry_attempts),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def generate_embeddings_batch(
        self, texts: list[str]
    ) -> list[Optional[list[float]]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            try:
                embedding = await self.generate_embedding(text)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Failed to generate embedding for text: {e}")
                embeddings.append(None)
        return embeddings


# Global embedding generator instance
embedding_generator = EmbeddingGenerator()
