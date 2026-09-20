"""
llm_provider.py — APEX
Multi-provider LLM gateway.
Priority: DeepSeek → Gemini → Groq → DeepSeek → OpenAI → Ollama → local fallback
"""

import os, json, urllib.request, urllib.error
from datetime import datetime

def _auto_detect_provider():
    if os.environ.get("DEEPSEEK_API_KEY"):  return "deepseek"
    if os.environ.get("GEMINI_API_KEY"):    return "gemini"
    if os.environ.get("GROQ_API_KEY"):      return "groq"
    if os.environ.get("OPENAI_API_KEY"):    return "openai"
    return "ollama"

LLM_PROVIDER = os.environ.get("LLM_PROVIDER") or _auto_detect_provider()
OLLAMA_MODEL  = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:1.5b")

def generate(system: str, messages: list, max_tokens: int = 1000) -> str:
    """Generate a response using the best available provider."""
    global LLM_PROVIDER
    provider = os.environ.get("LLM_PROVIDER") or LLM_PROVIDER

    try:
        if provider == "deepseek":
            return _deepseek(system, messages, max_tokens)
        elif provider == "gemini":
            return _gemini(system, messages, max_tokens)
        elif provider == "groq":
            return _groq(system, messages, max_tokens)
        elif provider == "openai":
            return _openai(system, messages, max_tokens)
        elif provider == "ollama":
            return _ollama(system, messages, max_tokens)
        else:
            return _local_fallback(messages)
    except Exception as e:
        # Try each fallback in order
        for fallback in ["deepseek","gemini","groq","ollama"]:
            if fallback != provider:
                try:
                    if fallback == "deepseek" and os.environ.get("DEEPSEEK_API_KEY"):
                        return _deepseek(system, messages, max_tokens)
                    elif fallback == "gemini" and os.environ.get("GEMINI_API_KEY"):
                        return _gemini(system, messages, max_tokens)
                    elif fallback == "groq" and os.environ.get("GROQ_API_KEY"):
                        return _groq(system, messages, max_tokens)
                    elif fallback == "ollama":
                        return _ollama(system, messages, max_tokens)
                except Exception:
                    continue
        return _local_fallback(messages)

def _deepseek(system, messages, max_tokens):
    key = os.environ.get("DEEPSEEK_API_KEY","")
    if not key: raise RuntimeError("No DeepSeek key")
    payload = json.dumps({
        "model": "deepseek-chat",
        "max_tokens": max_tokens,
        "messages": [{"role":"system","content":system}] + messages,
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=payload,
        headers={"Content-Type":"application/json","Authorization":f"Bearer {key}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]

def _gemini(system, messages, max_tokens):
    key = os.environ.get("GEMINI_API_KEY","")
    if not key: raise RuntimeError("No Gemini key")
    parts = [{"text": f"System: {system}\n\n"}]
    for m in messages:
        parts.append({"text": f"{m['role'].title()}: {m['content']}\n"})
    payload = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={key}"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]

def _groq(system, messages, max_tokens):
    key = os.environ.get("GROQ_API_KEY","")
    if not key: raise RuntimeError("No Groq key")
    payload = json.dumps({
        "model": "llama-3.1-8b-instant",
        "max_tokens": max_tokens,
        "messages": [{"role":"system","content":system}] + messages,
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={"Content-Type":"application/json","Authorization":f"Bearer {key}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]

def _openai(system, messages, max_tokens):
    key = os.environ.get("OPENAI_API_KEY","")
    if not key: raise RuntimeError("No OpenAI key")
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "max_tokens": max_tokens,
        "messages": [{"role":"system","content":system}] + messages,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={"Content-Type":"application/json","Authorization":f"Bearer {key}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]

def _ollama(system, messages, max_tokens):
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [{"role":"system","content":system}] + messages,
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=payload,
        headers={"Content-Type":"application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    return data["message"]["content"]

def _local_fallback(messages) -> str:
    last = messages[-1]["content"].lower() if messages else ""
    if any(w in last for w in ["hello","hi","hey"]):
        return "Hello Boss! I'm Nova — your AI YouTube agent. I'm running in offline mode. Add a free DeepSeek or Gemini key in Settings to unlock full capabilities."
    if "video" in last or "episode" in last:
        return "I'd love to create a video for you, Boss! I need an AI key to write the script. Add a free DeepSeek key (platform.deepseek.com) or Gemini key (aistudio.google.com) in Settings."
    if "status" in last:
        return "All agents standing by, Boss. Add a free API key in Settings to unlock full Nova intelligence."
    return "I'm Nova, your AI YouTube agent. Running in offline mode — add a free DeepSeek key in Settings to enable full conversation."

def health_check() -> dict:
    results = {}
    for name, key_env in [("deepseek","DEEPSEEK_API_KEY"),("gemini","GEMINI_API_KEY"),
                           ("groq","GROQ_API_KEY"),("openai","OPENAI_API_KEY")]:
        results[name] = "set" if os.environ.get(key_env) else "not_set"
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        results["ollama"] = "running"
    except Exception:
        results["ollama"] = "not_running"
    return results
