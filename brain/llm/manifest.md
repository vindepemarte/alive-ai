# Brain: LLM Module

Multi-provider LLM support for flexible model selection.

## Files
- `base.py` - Abstract BaseLLM class
- `zai.py` - ZAI API client (GLM models)
- `openrouter.py` - OpenRouter API client
- `ollama.py` - native Ollama `/api/chat` client
- `openai_compatible.py` - generic OpenAI-compatible chat-completions client
- `factory.py` - canonical provider aliases and shared provider construction
- `provider.py` - Factory for creating LLM clients

## Provider Selection
Set `LLM_PROVIDER` in `config/settings.json` or the environment.

Supported providers:
- `ollama` or `local`
- `openrouter`
- `zai`
- `openai-compatible`
- `lmstudio`
- `llamacpp`
- `vllm`
- `mlx`

## Task-Specific Models
- **main** - Primary conversation model
- **thinking** - Deep reasoning, complex decisions
- **fast** - Quick responses, impulses, subconscious

## Usage
```python
from brain.llm import get_main_llm, get_fast_llm, get_thinking_llm

llm = get_main_llm()
response = await llm.chat(messages, max_tokens=500)
```

## Environment Variables
- `LLM_PROVIDER` - provider name
- `ZAI_API_KEY`, `ZAI_MODEL_MAIN/FAST/THINKING`
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL_MAIN/FAST/THINKING`
- `OLLAMA_URL`, `OLLAMA_MODEL_MAIN/FAST/THINKING`
- `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_MODEL`
- `LMSTUDIO_BASE_URL`, `LMSTUDIO_MODEL`
- `LLAMACPP_BASE_URL`, `LLAMACPP_MODEL`
- `VLLM_BASE_URL`, `VLLM_MODEL`
- `MLX_BASE_URL`, `MLX_MODEL`

Generic OpenAI-compatible endpoints intentionally use no hidden-thinking or
reasoning controls by default. Provider-specific controls stay in the dedicated
ZAI, OpenRouter, and Ollama adapters.
