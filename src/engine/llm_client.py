"""
LLM Client — OpenAI-compatible API (official OpenAI or custom URL_ENDPOINT).

Reads from environment / .env:
  OPENAI_API_KEY   — API key (Bearer)
  URL_ENDPOINT     — host or full base URL (e.g. vtoken.viemind.ai)
  OPENAI_BASE_URL  — optional override (full base URL)
  LLM_PROVIDER     — openai | mock  (default: openai)
  LLM_MODEL        — chat model id
  LLM_MINI_MODEL   — lighter model for short tasks
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Load .env early so API modules work even if app entry forgot dotenv
try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(_env_path)
    load_dotenv()  # also CWD
except ImportError:
    pass


# Cloudflare on some proxies blocks the default Python/OpenAI User-Agent (error 1010)
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def normalize_base_url(endpoint: Optional[str]) -> str:
    """
    Build OpenAI-compatible base URL ending with /v1.

    Accepts:
      vtoken.viemind.ai
      https://vtoken.viemind.ai
      https://vtoken.viemind.ai/v1
    """
    if not endpoint or not str(endpoint).strip():
        return "https://api.openai.com/v1"

    url = str(endpoint).strip().rstrip("/")
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"
    if not url.endswith("/v1"):
        url = f"{url}/v1"
    return url


class MockLLMResponse:
    """Normalized chat response used across the engine."""

    def __init__(self, content, tool_calls=None):
        self.content = content or ""
        self.tool_calls = tool_calls or []


class ToolCall:
    """Simple tool-call object matching base_agent expectations."""

    def __init__(self, id: str, name: str, arguments: dict):
        self.id = id
        self.name = name
        self.arguments = arguments or {}


class LLMClient:
    def __init__(self, config=None):
        self.config = config or {}
        self.provider = (
            self.config.get("provider")
            or os.environ.get("LLM_PROVIDER", "openai")
        ).lower()
        self.model_name = (
            self.config.get("model")
            or os.environ.get("LLM_MODEL", "gemini-2.5-flash")
        )
        self.mini_model = (
            self.config.get("mini_model")
            or os.environ.get("LLM_MINI_MODEL", self.model_name)
        )
        self.client = None
        self.base_url = None

        if self.provider in ("openai", "azure_openai", "compatible"):
            self._init_openai()
        else:
            logger.info("Mock LLM Client initialized (provider=%s)", self.provider)
            self.provider = "mock"

    def _init_openai(self) -> None:
        api_key = (
            self.config.get("api_key")
            or os.environ.get("OPENAI_API_KEY")
        )
        endpoint = (
            self.config.get("base_url")
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("URL_ENDPOINT")
        )

        if not api_key:
            logger.warning("OPENAI_API_KEY is not set. Falling back to Mock LLM.")
            self.provider = "mock"
            self.client = None
            return

        try:
            from openai import OpenAI
        except ImportError as e:
            logger.error("openai package not installed: %s. Falling back to Mock.", e)
            self.provider = "mock"
            self.client = None
            return

        self.base_url = normalize_base_url(endpoint)
        default_headers = {
            "User-Agent": os.environ.get("OPENAI_USER_AGENT", _DEFAULT_UA),
            "Accept": "application/json",
        }

        self.client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            default_headers=default_headers,
        )
        self.provider = "openai"
        logger.info(
            "OpenAI-compatible LLM Client initialized: base_url=%s model=%s",
            self.base_url,
            self.model_name,
        )

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def chat(
        self,
        messages,
        tools=None,
        temperature=0.7,
        max_tokens=500,
        model: Optional[str] = None,
    ):
        if self.provider == "openai" and self.client is not None:
            try:
                return self._openai_chat(
                    messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=model or self.model_name,
                )
            except Exception as e:
                logger.error("OpenAI API Error: %s", e)
                return MockLLMResponse(content=f"[Lỗi API OpenAI: {str(e)}]")
        return self._mock_chat(messages)

    def chat_with_tool_results(self, messages, tool_results):
        """
        Second-pass LLM call after tools ran.
        Appends tool results as a user message (compatible with most gateways).
        """
        follow_up = list(messages) if messages else []
        follow_up.append(
            {
                "role": "user",
                "content": (
                    "Kết quả tool (dùng để trả lời user, không lặp lại JSON thô):\n"
                    + json.dumps(tool_results, ensure_ascii=False, default=str)
                ),
            }
        )
        return self.chat(follow_up, temperature=0.5, max_tokens=600)

    def check_claim(self, claim, context, prompt):
        """Lightweight fact-check helper used by safety / supervisor paths."""
        if self.provider != "openai" or self.client is None:
            return {"is_true": True, "correction": ""}

        system = (
            prompt
            or "Bạn là bộ kiểm tra fact. Trả về JSON: "
            '{"is_true": bool, "correction": string}'
        )
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nClaim:\n{claim}",
            },
        ]
        try:
            resp = self.chat(
                messages,
                temperature=0,
                max_tokens=200,
                model=self.mini_model,
            )
            text = (resp.content or "").strip()
            # Try parse JSON object from response
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1 and end > start:
                data = json.loads(text[start : end + 1])
                return {
                    "is_true": bool(data.get("is_true", True)),
                    "correction": str(data.get("correction", "")),
                }
        except Exception as e:
            logger.warning("check_claim failed: %s", e)
        return {"is_true": True, "correction": ""}

    def generate(self, prompt, temperature=0.7):
        """Return a short list of suggestion strings."""
        if self.provider != "openai" or self.client is None:
            return ["Suggestion 1", "Suggestion 2", "Suggestion 3"]

        messages = [
            {
                "role": "system",
                "content": (
                    "Trả về đúng 3 gợi ý ngắn, mỗi gợi ý một dòng, "
                    "không đánh số, không markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        try:
            resp = self.chat(
                messages,
                temperature=temperature,
                max_tokens=200,
                model=self.mini_model,
            )
            lines = [
                ln.strip(" -*\t")
                for ln in (resp.content or "").splitlines()
                if ln.strip()
            ]
            return lines[:3] or ["Suggestion 1", "Suggestion 2", "Suggestion 3"]
        except Exception as e:
            logger.warning("generate failed: %s", e)
            return ["Suggestion 1", "Suggestion 2", "Suggestion 3"]

    # ─────────────────────────────────────────
    # OpenAI implementation
    # ─────────────────────────────────────────

    def _openai_chat(
        self,
        messages,
        tools=None,
        temperature=0.7,
        max_tokens=500,
        model: Optional[str] = None,
    ) -> MockLLMResponse:
        kwargs: dict[str, Any] = {
            "model": model or self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Only pass tools when non-empty (some proxies reject null/empty tools)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        content = message.content or ""
        # Some Gemini-via-proxy models put text in reasoning_content with empty content
        reasoning = getattr(message, "reasoning_content", None)
        if not content and reasoning:
            content = str(reasoning)

        tool_calls = []
        raw_calls = getattr(message, "tool_calls", None) or []
        for tc in raw_calls:
            name = ""
            arguments: dict = {}
            try:
                name = tc.function.name
                raw_args = tc.function.arguments or "{}"
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
            except Exception as e:
                logger.warning("Failed to parse tool call: %s", e)
                arguments = {}
            tool_calls.append(
                ToolCall(
                    id=getattr(tc, "id", "") or "",
                    name=name,
                    arguments=arguments if isinstance(arguments, dict) else {},
                )
            )

        return MockLLMResponse(content=content, tool_calls=tool_calls)

    def _mock_chat(self, messages):
        last_msg = messages[-1]["content"] if messages else ""
        logger.debug("Mock LLM generating response for: %s...", str(last_msg)[:50])
        response_content = (
            f"Đây là câu trả lời mô phỏng từ AI dựa trên tin nhắn: "
            f"'{str(last_msg)[:50]}...'. Hãy kết nối API thật để có phản hồi thông minh."
        )
        return MockLLMResponse(content=response_content)
