"""Document embedding generation for RAG and semantic search."""

import logging
from typing import List, Optional

from .config import Config, get_config

logger = logging.getLogger(__name__)

# Lazy import to avoid loading heavy dependencies unless needed
_sentence_transformers = None
_SentenceTransformer = None


def _get_sentence_transformer():
    """Lazy load sentence-transformers to avoid import overhead."""
    global _sentence_transformers, _SentenceTransformer
    if _SentenceTransformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            _SentenceTransformer = SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for embeddings. "
                "Install it with: pip install sentence-transformers"
            )
    return _SentenceTransformer


class DocumentEmbedder:
    """Generates embeddings for document text using local models.
    
    Supports:
    - sentence-transformers models (default: all-MiniLM-L6-v2)
    - Can be extended for OpenAI-compatible embedding APIs
    """

    # Popular embedding models with their dimensions
    MODELS = {
        "all-MiniLM-L6-v2": 384,           # Fast, good quality, small
        "all-mpnet-base-v2": 768,          # Better quality, slower
        "paraphrase-MiniLM-L6-v2": 384,    # Good for paraphrase detection
        "multi-qa-MiniLM-L6-cos-v1": 384,  # Optimized for Q&A
    }

    def __init__(
        self,
        config: Optional[Config] = None,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        """Initialize the embedder.
        
        Args:
            config: DocTagger configuration
            model_name: Name of the sentence-transformers model to use
        """
        self.config = config or get_config()
        self.model_name = model_name
        self._model = None
        self._enabled = True

    @property
    def model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            try:
                SentenceTransformer = _get_sentence_transformer()
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Embedding model loaded: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
                self._enabled = False
                raise
        return self._model

    @property
    def dimensions(self) -> int:
        """Get the embedding dimensions for the current model."""
        return self.MODELS.get(self.model_name, 384)

    @property
    def enabled(self) -> bool:
        """Check if embeddings are enabled and available."""
        return self._enabled

    def embed_text(self, text: str, max_chars: int = 8000) -> Optional[List[float]]:
        """Generate embedding for a text string.
        
        Args:
            text: The text to embed
            max_chars: Maximum characters to use (models have token limits)
            
        Returns:
            List of floats representing the embedding, or None if failed
        """
        if not self._enabled:
            return None

        try:
            # Truncate text if too long (most models have ~512 token limit)
            truncated = text[:max_chars] if len(text) > max_chars else text
            
            # Generate embedding
            embedding = self.model.encode(
                truncated,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            
            # Convert to list of floats for JSON serialization
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def embed_chunks(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> List[dict]:
        """Generate embeddings for text chunks (for long documents).
        
        This is useful for RAG where you want to embed and retrieve
        specific sections of a document.
        
        Args:
            text: The full document text
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            
        Returns:
            List of dicts with 'text', 'start', 'end', 'embedding' keys
        """
        if not self._enabled:
            return []

        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]
            
            embedding = self.embed_text(chunk_text)
            if embedding:
                chunks.append({
                    "text": chunk_text,
                    "start": start,
                    "end": end,
                    "embedding": embedding,
                })
            
            start += chunk_size - overlap
            if start >= len(text):
                break
                
        return chunks

    def embed_with_metadata(
        self,
        text: str,
        title: Optional[str] = None,
        entities: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[List[float]]:
        """Generate embedding with enriched context.
        
        Prepends metadata to text for richer embeddings that capture
        document context.
        
        Args:
            text: Document text
            title: Document title
            entities: List of entities mentioned
            tags: List of tags
            
        Returns:
            Embedding vector or None
        """
        # Build enriched text with metadata prefix
        parts = []
        
        if title:
            parts.append(f"Title: {title}")
        if entities:
            parts.append(f"Entities: {', '.join(entities[:10])}")
        if tags:
            parts.append(f"Tags: {', '.join(tags[:10])}")
        
        if parts:
            enriched_text = "\n".join(parts) + "\n\n" + text
        else:
            enriched_text = text
            
        return self.embed_text(enriched_text)


# Global embedder instance (lazy loaded)
_embedder: Optional[DocumentEmbedder] = None


def get_embedder(model_name: str = "all-MiniLM-L6-v2") -> DocumentEmbedder:
    """Get or create global embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = DocumentEmbedder(model_name=model_name)
    return _embedder
