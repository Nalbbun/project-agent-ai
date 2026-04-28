FROM /srv/llm/merged/ollama/pm-agent.gguf
PARAMETER temperature 0.2
SYSTEM You are the PM agent. Return structured JSON only.
