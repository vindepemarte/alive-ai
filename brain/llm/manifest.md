# Brain: LLM Module

Multi-provider LLM support for flexible model selection.

## Files
- `base.py` - Abstract BaseLLM class
- `zai.py` - ZAI API client (GLM models)
- `openrouter.py` - OpenRouter API client
- `provider.py` - Factory for creating LLM clients

## Provider Selection
Set `LLM_PROVIDER` env var: `zai` (default) or `openrouter`

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
- `LLM_PROVIDER` - zai or openrouter
- `ZAI_API_KEY`, `ZAI_MODEL_MAIN/FAST/THINKING`
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL_MAIN/FAST/THINKING`
