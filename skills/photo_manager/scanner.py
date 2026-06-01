"""
Skills: Photo Scanner
Incremental scanner for mypics folder with category support and vector memory
"""

import os
import json
import hashlib
import random
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List
from collections import deque


class PhotoScanner:
    """Incremental photo scanner with category support, vector search, and no-repeat tracking"""

    # Category tiers (higher = more intimate)
    TIERS = {
        "public": 0,
        "premium": 1,
        "premium_plus": 2,
        "elite": 3
    }

    def __init__(self, mypics_path: Path, embedding_service=None, vector_store=None, no_repeat_count: int = 20):
        self.path = Path(mypics_path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.path / ".index.json"
        self.index = self._load_index()

        # For semantic search
        self.embedding_service = embedding_service
        self.vector_store = vector_store

        # Photo vectors stored separately (photo: prefix in Redis)
        self.photo_vectors = {}  # filename -> embedding

        # Track recently sent to avoid repeats
        self.recently_sent = deque(maxlen=no_repeat_count)
        self.no_repeat_count = no_repeat_count

    def _load_index(self) -> dict:
        if self.index_file.exists():
            return json.loads(self.index_file.read_text())
        return {}

    def _save_index(self):
        self.index_file.write_text(json.dumps(self.index, indent=2))

    def _hash(self, filepath: str) -> str:
        """Get file hash for change detection"""
        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()[:8]
        except:
            return "unknown"

    def _get_category(self, filepath: str) -> str:
        """Get category from folder name"""
        rel_path = os.path.relpath(filepath, self.path)
        parts = rel_path.split(os.sep)
        if len(parts) > 1:
            category = parts[0].lower()
            if category in self.TIERS:
                return category
        return "public"

    def scan_new(self) -> list:
        """Scan for new/changed photos in all subdirectories"""
        extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        added = []

        # Walk through all subdirectories
        for root, dirs, files in os.walk(self.path):
            for filename in files:
                if filename.lower().endswith(extensions):
                    filepath = os.path.join(root, filename)

                    # Use relative path as key
                    rel_path = os.path.relpath(filepath, self.path)

                    # Skip if already indexed with same hash
                    current_hash = self._hash(filepath)
                    if rel_path in self.index and self.index[rel_path].get("hash") == current_hash:
                        continue

                    # Get category from folder
                    category = self._get_category(filepath)

                    # Get description from .txt file
                    base_name = os.path.splitext(filename)[0]
                    txt_path = os.path.join(root, f"{base_name}.txt")
                    description = ""
                    if os.path.exists(txt_path):
                        with open(txt_path) as f:
                            description = f.read().strip()
                    else:
                        # Generate description from filename
                        description = base_name.replace("_", " ").replace("-", " ")

                    self.index[rel_path] = {
                        "hash": current_hash,
                        "description": description,
                        "category": category,
                        "tier": self.TIERS.get(category, 0),
                        "scanned_at": datetime.now().isoformat()
                    }
                    added.append(rel_path)

                    # Store in vector memory if embedding service available
                    if self.embedding_service and self.vector_store:
                        self._store_photo_vector(rel_path, description, category)

        if added:
            self._save_index()

        return added

    def _store_photo_vector(self, rel_path: str, description: str, category: str):
        """Store photo description as vector in Redis"""
        try:
            embedding = self.embedding_service.embed(description)
            self.photo_vectors[rel_path] = embedding

            # Also store in Redis with photo: prefix
            if self.vector_store and self.vector_store._connected:
                import time
                import numpy as np

                photo_id = f"photo:{int(time.time() * 1000)}"
                embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()

                self.vector_store.redis.hset(photo_id, mapping={
                    "path": rel_path,
                    "description": description,
                    "category": category,
                    "timestamp": datetime.now().isoformat()
                })
                self.vector_store.redis.hset(photo_id, "embedding", embedding_bytes)

        except Exception as e:
            print(f"[PhotoScanner] Vector store error: {e}")

    def mark_sent(self, photo_path: str):
        """Mark a photo as recently sent"""
        self.recently_sent.append(photo_path)

    def was_recently_sent(self, photo_path: str) -> bool:
        """Check if photo was recently sent"""
        return photo_path in self.recently_sent

    def search_photos(self, query: str, min_tier: int = 0, max_tier: int = 3, limit: int = 5, exclude_recent: bool = True) -> List[Tuple[str, str, str, float]]:
        """Search photos by semantic similarity to query, excluding recently sent"""
        if not self.embedding_service:
            # Fallback to random
            result = self.get_random(min_tier=min_tier, max_tier=max_tier)
            if result:
                return [(result[0], result[1], result[2], 0.0)]
            return []

        try:
            # Get query embedding
            query_embedding = self.embedding_service.embed(query)

            # Calculate similarity to all indexed photos
            results = []
            for rel_path, data in self.index.items():
                tier = data.get("tier", 0)
                if min_tier <= tier <= max_tier:
                    # Skip recently sent
                    if exclude_recent and rel_path in self.recently_sent:
                        continue

                    # Get or create embedding for this photo
                    if rel_path in self.photo_vectors:
                        photo_embedding = self.photo_vectors[rel_path]
                    else:
                        # Create embedding from description
                        photo_embedding = self.embedding_service.embed(data.get("description", ""))
                        self.photo_vectors[rel_path] = photo_embedding

                    # Calculate similarity
                    import numpy as np
                    v1 = np.array(query_embedding)
                    v2 = np.array(photo_embedding)
                    similarity = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

                    results.append((
                        rel_path,
                        data.get("description", ""),
                        data.get("category", "public"),
                        similarity
                    ))

            # Sort by similarity (highest first)
            results.sort(key=lambda x: x[3], reverse=True)

            # If no results (all recently sent), try again without exclusion
            if not results and exclude_recent:
                return self.search_photos(query, min_tier, max_tier, limit, exclude_recent=False)

            return results[:limit]

        except Exception as e:
            print(f"[PhotoScanner] Search error: {e}")
            result = self.get_random(min_tier=min_tier, max_tier=max_tier)
            if result:
                return [(result[0], result[1], result[2], 0.0)]
            return []

    def get_by_category(self, category: str) -> list:
        """Get photos by category"""
        return [
            (name, data)
            for name, data in self.index.items()
            if data.get("category") == category
        ]

    def get_by_tier(self, max_tier: int) -> list:
        """Get photos up to a certain tier level"""
        return [
            (name, data)
            for name, data in self.index.items()
            if data.get("tier", 0) <= max_tier
        ]

    def get_random(self, category: str = None, min_tier: int = 0, max_tier: int = 3, exclude_recent: bool = True) -> tuple | None:
        """Get random photo, optionally filtered by category or tier, avoiding recent sends"""
        photos = [
            (name, data)
            for name, data in self.index.items()
            if min_tier <= data.get("tier", 0) <= max_tier
        ]
        if category:
            photos = [(n, d) for n, d in photos if d.get("category") == category]

        # Exclude recently sent photos
        if exclude_recent:
            photos = [(n, d) for n, d in photos if n not in self.recently_sent]

        # If all photos excluded, allow repeats but log warning
        if not photos and exclude_recent:
            print(f"[PhotoScanner] All photos recently sent, allowing repeat")
            return self.get_random(category, min_tier, max_tier, exclude_recent=False)

        if not photos:
            return None

        name, data = random.choice(photos)
        return (name, data.get("description", ""), data.get("category", "public"))

    def get_for_context(self, context: str, arousal: float = 0.5, desire: float = 0.5) -> Optional[Tuple[str, str, str]]:
        """Get photo that matches context and arousal level using semantic search"""
        # Determine appropriate tier based on arousal
        if arousal < 0.4:
            min_tier, max_tier = 0, 1
        elif arousal < 0.6:
            min_tier, max_tier = 1, 2
        elif arousal < 0.8:
            min_tier, max_tier = 1, 3
        else:
            min_tier, max_tier = 2, 3

        # Search for matching photos
        results = self.search_photos(context, min_tier=min_tier, max_tier=max_tier, limit=5)

        if results:
            # Pick from top results with some randomness
            import random
            top_results = results[:3] if len(results) >= 3 else results
            chosen = random.choice(top_results)
            return (chosen[0], chosen[1], chosen[2])

        return None

    def get_random_intimate(self, tier: int = 3) -> tuple | None:
        """Get random intimate photo (tier 2-3)"""
        return self.get_random(min_tier=2, max_tier=tier)

    def get_random_safe(self) -> tuple | None:
        """Get random safe photo (tier 0-1)"""
        return self.get_random(min_tier=0, max_tier=1)

    def get_all(self) -> dict:
        """Get all indexed photos"""
        return self.index.copy()

    def stats(self) -> dict:
        """Get index statistics"""
        stats = {"total": len(self.index), "categories": {}}
        for name, data in self.index.items():
            cat = data.get("category", "unknown")
            stats["categories"][cat] = stats["categories"].get(cat, 0) + 1
        return stats
