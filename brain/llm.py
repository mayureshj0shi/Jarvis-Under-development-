import os

from openai import OpenAI
from openai import APIConnectionError, APIError, RateLimitError

from core.config import get_config


class LLMClient:
    def __init__(self):
        cfg = get_config()["llm"]
        self.temperature = cfg.get("temperature", 0.7)
        self.max_tokens = cfg.get("max_tokens", 1024)
        self.providers = []
        for p in cfg.get("providers", []):
            if not p.get("enabled", True):
                continue
            env_key = p.get("api_key_env")
            if env_key:
                key = os.environ.get(env_key) or "missing"
            else:
                key = p.get("api_key") or "ollama"
            client = OpenAI(base_url=p["base_url"], api_key=key)
            self.providers.append(
                {"name": p["name"], "client": client, "model": p["model"]}
            )

    def chat(self, messages, tools=None, tool_choice="auto"):
        last_err = None
        for prov in self.providers:
            try:
                kwargs = dict(
                    model=prov["model"],
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = tool_choice
                resp = prov["client"].chat.completions.create(**kwargs)
                print(f"[llm] provider: {prov['name']}")
                return resp.choices[0].message
            except (RateLimitError, APIConnectionError, APIError) as e:
                last_err = e
                print(f"[llm] provider {prov['name']} failed: {e}")
                continue
        if last_err:
            raise last_err
        raise RuntimeError("No enabled LLM providers configured")

    def chat_stream(self, messages, tools=None, tool_choice="auto"):
        """Like chat() but streams. Returns (provider_name, chunk_generator)."""
        last_err = None
        for prov in self.providers:
            try:
                kwargs = dict(
                    model=prov["model"],
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True,
                )
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = tool_choice
                stream = prov["client"].chat.completions.create(**kwargs)
                print(f"[llm] provider: {prov['name']} (stream)")
                return prov["name"], stream
            except (RateLimitError, APIConnectionError, APIError) as e:
                last_err = e
                print(f"[llm] provider {prov['name']} failed: {e}")
                continue
        if last_err:
            raise last_err
        raise RuntimeError("No enabled LLM providers configured")
