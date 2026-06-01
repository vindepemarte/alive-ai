"""
Brain: Vector Memory Store
Redis-based vector storage for semantic memory search
"""

import json
import redis
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
import numpy as np

# Redis connection settings
REDIS_HOST = "redis"
REDIS_PORT = 6379

# Memory archive path - detect Docker vs local development
_docker_archive = Path("/data/memory_archive")
_local_archive = Path(__file__).parent.parent.parent / "data" / "memory_archive"
ARCHIVE_PATH = _docker_archive if _docker_archive.parent.exists() else _local_archive


class VectorMemoryStore:
    """Redis-based vector memory with semantic search and archiving"""

    INDEX_NAME = "memory_index"
    MEMORY_PREFIX = "mem:"

    def __init__(self, embedding_service, dimension: int = 384, user_id: str = "default", bot_id: str = "alive_ai"):
        """
        Initialize the vector memory store.

        Args:
            embedding_service: Service for generating embeddings
            dimension: Embedding dimension (default 384)
            user_id: User ID for per-user memory isolation
            bot_id: Bot ID for per-bot memory isolation
        """
        self.embeddings = embedding_service
        self.dimension = dimension
        self.user_id = user_id
        self.bot_id = bot_id.lower()
        self.redis = None
        self._connected = False

    @staticmethod
    def _decode(val):
        """Decode bytes to str if needed"""
        return val.decode("utf-8") if isinstance(val, bytes) else val

    def connect(self) -> bool:
        """Connect to Redis and create index if needed"""
        try:
            self.redis = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=False  # binary-safe for embeddings
            )
            self.redis.ping()
            self._connected = True
            print(f"[VectorStore] Connected to Redis")

            # Create vector index if not exists
            self._create_index()
            return True
        except Exception as e:
            print(f"[VectorStore] Redis connection failed: {e}")
            self._connected = False
            return False

    def _create_index(self):
        """Create RediSearch vector index"""
        try:
            # Check if index exists
            indices = self.redis.execute_command("FT._LIST")
            decoded_indices = [self._decode(i) for i in indices]
            if self.INDEX_NAME in decoded_indices:
                print(f"[VectorStore] Index '{self.INDEX_NAME}' already exists")
                return

            # Create the index with vector field and user_id/bot_id for filtering
            self.redis.execute_command(
                "FT.CREATE", self.INDEX_NAME,
                "ON", "HASH",
                "PREFIX", "1", self.MEMORY_PREFIX,
                "SCHEMA",
                "timestamp", "NUMERIC", "SORTABLE",
                "role", "TAG",
                "user_id", "TAG",
                "bot_id", "TAG",
                "content", "TEXT",
                "embedding", "VECTOR", "HNSW", "6",
                "TYPE", "FLOAT32",
                "DIM", str(self.dimension),
                "DISTANCE_METRIC", "COSINE"
            )
            print(f"[VectorStore] Created vector index '{self.INDEX_NAME}'")
        except Exception as e:
            print(f"[VectorStore] Index creation error: {e}")

    def _ensure_connected(self) -> bool:
        """Reconnect to Redis if disconnected"""
        if self._connected:
            try:
                self.redis.ping()
                return True
            except Exception:
                self._connected = False
        # Try to reconnect
        return self.connect()

    def store(self, role: str, content: str, metadata: Dict = None) -> str:
        """Store a memory with embedding, scoped to user_id"""
        if not self._ensure_connected():
            return ""

        import time
        # Include bot_id and user_id in the key for isolation
        memory_id = f"{self.MEMORY_PREFIX}{self.bot_id}:{self.user_id}:{int(time.time() * 1000)}"
        timestamp = datetime.now().isoformat()

        # Generate embedding
        embedding = self.embeddings.embed(content)
        embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()

        # Store in Redis hash with user_id and bot_id
        memory_data = {
            "timestamp": timestamp,
            "role": role,
            "user_id": self.user_id,
            "bot_id": self.bot_id,
            "content": content,
            "metadata": json.dumps(metadata or {}),
        }

        try:
            # Store all fields including binary embedding in one call
            memory_data["embedding"] = embedding_bytes
            self.redis.hset(memory_id, mapping=memory_data)
            print(f"[VectorStore] Stored memory: {content[:50]}...")
            return memory_id
        except Exception as e:
            print(f"[VectorStore] Store error: {e}")
            return ""

    def search(self, query: str, limit: int = 5, min_score: float = 0.5) -> List[Dict]:
        """Search for similar memories using semantic search, filtered by user_id"""
        if not self._ensure_connected():
            return []

        # Embed the query
        query_embedding = self.embeddings.embed(query)
        query_vector = np.array(query_embedding, dtype=np.float32).tobytes()

        try:
            # Use FT.SEARCH with vector similarity, filtered by user_id AND bot_id
            # KNN search for nearest neighbors within user's memories with this bot
            results = self.redis.execute_command(
                "FT.SEARCH", self.INDEX_NAME,
                f"(@user_id:{{{self.user_id}}} @bot_id:{{{self.bot_id}}})=>[KNN {limit} @embedding $query_vec AS score]",
                "PARAMS", "2", "query_vec", query_vector,
                "RETURN", "4", "timestamp", "role", "content", "metadata",
                "DIALECT", "2"
            )

            memories = []
            if results and len(results) > 1:
                i = 1
                while i < len(results) - 1:
                    key = self._decode(results[i])
                    fields = results[i + 1] if i + 1 < len(results) else []
                    memory = {"id": key}
                    for j in range(0, len(fields) - 1, 2):
                        fn = self._decode(fields[j])
                        fv = self._decode(fields[j + 1])
                        if fn == "metadata":
                            try: memory[fn] = json.loads(fv)
                            except: memory[fn] = {}
                        else:
                            memory[fn] = fv
                    memories.append(memory)
                    i += 2
            return memories[:limit]

        except Exception as e:
            print(f"[VectorStore] Search error: {e}")
            return []

    def search_simple(self, query: str, limit: int = 5) -> List[Dict]:
        """Simple text search fallback if vector search fails, filtered by user_id"""
        if not self._ensure_connected():
            return []

        try:
            results = self.redis.execute_command(
                "FT.SEARCH", self.INDEX_NAME,
                f"@user_id:{{{self.user_id}}} @bot_id:{{{self.bot_id}}} @content:{query}",
                "RETURN", "3", "timestamp", "role", "content",
                "LIMIT", "0", str(limit)
            )

            return self._parse_results(results)
        except Exception as e:
            print(f"[VectorStore] Simple search error: {e}")
            return []

    def _parse_results(self, results) -> List[Dict]:
        """Parse FT.SEARCH results with bytes decoding"""
        memories = []
        if not results or len(results) <= 1:
            return memories
        i = 1
        while i < len(results) - 1:
            key = self._decode(results[i])
            fields = results[i + 1] if i + 1 < len(results) else []
            memory = {"id": key}
            for j in range(0, len(fields) - 1, 2):
                memory[self._decode(fields[j])] = self._decode(fields[j + 1])
            memories.append(memory)
            i += 2
        return memories

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get most recent memories for this user"""
        if not self._ensure_connected():
            return []

        try:
            results = self.redis.execute_command(
                "FT.SEARCH", self.INDEX_NAME,
                f"@user_id:{{{self.user_id}}} @bot_id:{{{self.bot_id}}}",
                "RETURN", "3", "timestamp", "role", "content",
                "SORTBY", "timestamp",
                "DESC",
                "LIMIT", "0", str(limit)
            )

            return self._parse_results(results)
        except Exception as e:
            print(f"[VectorStore] Get recent error: {e}")
            return []

    def count(self) -> int:
        """Count total stored memories for this user"""
        if not self._ensure_connected():
            return 0

        try:
            keys = self.redis.keys(f"{self.MEMORY_PREFIX}{self.bot_id}:{self.user_id}:*")
            count = len(keys) if keys else 0
            return count
        except Exception as e:
            print(f"[VectorStore] Count error: {e}")
            return 0

    def archive_old_memories(self, max_in_redis: int = 1000):
        """Archive old memories to disk, keep recent ones in Redis (per-user)"""
        if not self._ensure_connected():
            return

        count = self.count()
        if count <= max_in_redis:
            return

        print(f"[VectorStore] Archiving old memories for user {self.user_id} ({count} > {max_in_redis})...")

        try:
            results = self.redis.execute_command(
                "FT.SEARCH", self.INDEX_NAME,
                f"@user_id:{{{self.user_id}}} @bot_id:{{{self.bot_id}}}",
                "RETURN", "4", "timestamp", "role", "content", "metadata",
                "SORTBY", "timestamp",
                "ASC",
                "LIMIT", "0", str(count - max_in_redis)
            )

            ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
            to_archive = self._parse_results(results)
            # Save to archive file
            archive_file = ARCHIVE_PATH / f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            with open(archive_file, 'w') as f:
                for mem in to_archive:
                    f.write(json.dumps(mem) + '\n')

            # Delete from Redis
            for mem in to_archive:
                self.redis.delete(mem["id"])

            print(f"[VectorStore] Archived {len(to_archive)} memories to {archive_file}")

        except Exception as e:
            print(f"[VectorStore] Archive error: {e}")

    def close(self):
        """Close Redis connection"""
        if self.redis:
            self.redis.close()
