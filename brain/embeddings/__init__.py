"""
Brain: Embeddings
Local embedding service using sentence-transformers/all-MiniLM-L6-v2
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import os
import threading

from pathlib import Path

# Model cache directory
MODEL_CACHE_DIR = str(Path(__file__).parent.parent.parent / ".cache" / "huggingface")


class EmbeddingService:
    """Local embedding service for semantic memory"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", preload: bool = True):
        self.model_name = model_name
        self.model = None
        self._load_lock = threading.Lock()
        self.dimension = 384  # MiniLM-L6-v2 dimension
        if preload:
            # Pre-load in background to not block startup
            t = threading.Thread(target=self.load, daemon=True)
            t.start()

    def load(self):
        """Load the embedding model (thread-safe lazy loading)"""
        if self.model is not None:
            return self.model
        with self._load_lock:
            if self.model is None:
                print(f"[Embeddings] Loading model {self.model_name}...")

                # Set HF token if available
                hf_token = os.environ.get("HF_TOKEN", "")
                if hf_token:
                    os.environ["HUGGING_FACE_HUB_TOKEN"] = hf_token
                    print(f"[Embeddings] Using HuggingFace token for faster downloads")

                os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
                self.model = SentenceTransformer(
                    self.model_name,
                    cache_folder=MODEL_CACHE_DIR,
                    token=hf_token if hf_token else None
                )
                print(f"[Embeddings] Model loaded! Dimension: {self.dimension}")
        return self.model

    def embed(self, text: str) -> List[float]:
        """Embed a single text into a vector"""
        self.load()
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts at once (more efficient)"""
        self.load()
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


# Global instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
