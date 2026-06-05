# Brain - Intelligence Center

Multi-provider LLM, memory systems, and subconscious processing.

## Modules
- `memory/` - Token-efficient memory with vector search
  - `vector_store.py` - Redis-based semantic memory
  - `episodic.py` - Conversation memory
  - `working.py` - Working memory (RAM)
  - `layers.py` - Biological memory layer compiler for prompt context
- `llm/` - Multi-provider LLM support (see llm/manifest.md)
- `subconscious/` - 24/7 living brain (see subconscious/manifest.md)
- `embeddings/` - Sentence transformers for semantic search
- `stt/` - Speech-to-text (Google, Whisper)

## Key Files
- `__init__.py` - Main Memory class
- `index.py` - Fast memory index

## Features
- Multi-provider: ZAI or OpenRouter
- Semantic search via embeddings (all-MiniLM-L6-v2)
- Redis vector storage with archiving
- Layered context assembly across working, episodic, semantic, emotional, autobiographical, dream, and shadow memory
- Subconscious impulse generation
