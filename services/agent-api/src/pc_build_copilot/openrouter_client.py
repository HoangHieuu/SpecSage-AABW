from collections.abc import Callable, Sequence
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json

from pc_build_copilot.llm_config import OpenRouterSettings


class OpenRouterError(RuntimeError):
    pass


class OpenRouterHTTPError(OpenRouterError):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"OpenRouter request failed with HTTP {status_code}")
        self.status_code = status_code


Transport = Callable[[Request, float], bytes]
ChatMessage = dict[str, str]


class OpenRouterClient:
    def __init__(
        self,
        settings: OpenRouterSettings,
        transport: Transport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport or _default_transport

    @property
    def model(self) -> str:
        return self._settings.model

    def chat_json(self, messages: Sequence[ChatMessage]) -> dict[str, Any]:
        if not self._settings.enabled or not self._settings.api_key:
            raise OpenRouterError("OpenRouter API key is not configured")

        body = self._chat_body(messages, json_mode=True)
        try:
            payload = self._send(body)
        except OpenRouterHTTPError as exc:
            if exc.status_code not in {400, 404, 422}:
                raise
            payload = self._send(self._chat_body(messages, json_mode=False))

        return self._extract_json(payload)

    def _chat_body(self, messages: Sequence[ChatMessage], json_mode: bool) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self._settings.model,
            "messages": list(messages),
            "temperature": 0.2,
            "max_tokens": self._settings.max_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
            body["provider"] = {"require_parameters": True}
        return body

    def _send(self, body: dict[str, Any]) -> bytes:
        request = Request(
            f"{self._settings.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._settings.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self._settings.site_url,
                "X-OpenRouter-Title": self._settings.app_name,
            },
            method="POST",
        )

        try:
            return self._transport(request, self._settings.timeout_seconds)
        except HTTPError as exc:
            raise OpenRouterHTTPError(exc.code) from exc
        except URLError as exc:
            raise OpenRouterError("OpenRouter request failed before receiving a response") from exc
        except TimeoutError as exc:
            raise OpenRouterError("OpenRouter request timed out") from exc

    def _extract_json(self, payload: bytes) -> dict[str, Any]:
        try:
            data = json.loads(payload.decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OpenRouterError("OpenRouter response did not match chat completion format") from exc

        if isinstance(content, dict):
            return content
        if not isinstance(content, str):
            raise OpenRouterError("OpenRouter response content was not JSON text")
        return _parse_json_content(content)


def _default_transport(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _parse_json_content(content: str) -> dict[str, Any]:
    cleaned = _strip_code_fence(content.strip())
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise OpenRouterError("OpenRouter response content did not contain a JSON object")
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise OpenRouterError("OpenRouter response content was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise OpenRouterError("OpenRouter response content was not a JSON object")
    return parsed


def _strip_code_fence(content: str) -> str:
    if not content.startswith("```"):
        return content
    lines = content.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
