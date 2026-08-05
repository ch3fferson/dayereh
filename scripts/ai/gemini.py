from typing import Any, Iterator

from google import genai
from google.genai import types


class GeminiClient:

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.5-flash",
        system_instruction: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        max_output_tokens: int | None = None,
        stop_sequences: list[str] | None = None,
    ):
        if not api_key:
            raise ValueError("api_key is required")

        self.model = model
        self.client = genai.Client(api_key=api_key)

        model_info = self.client.models.get(model=model)

        self.input_token_limit = model_info.input_token_limit
        self.output_token_limit = model_info.output_token_limit

        if not self.input_token_limit:
            raise RuntimeError(
                f"Could not determine input token limit for {model}"
            )

        if max_output_tokens is not None:
            max_output_tokens = min(
                max_output_tokens,
                self.output_token_limit or max_output_tokens,
            )

        self.config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
            stop_sequences=stop_sequences,
        )

        self._chat = None

    def send(
        self,
        text: str,
        remember: bool = False,
        **overrides: Any,
    ) -> str:

        if not text:
            return ""

        config = self._config_with_overrides(overrides)

        if remember:

            if self._chat is None:
                self._chat = self.client.chats.create(
                    model=self.model,
                    config=config,
                )

            response = self._chat.send_message(text)

        else:

            response = self.client.models.generate_content(
                model=self.model,
                contents=text,
                config=config,
            )

        return response.text or ""

    def stream(
        self,
        text: str,
        remember: bool = False,
        **overrides: Any,
    ) -> Iterator[str]:

        if not text:
            return

        config = self._config_with_overrides(overrides)

        if remember:

            if self._chat is None:
                self._chat = self.client.chats.create(
                    model=self.model,
                    config=config,
                )

            stream = self._chat.send_message_stream(text)

        else:

            stream = self.client.models.generate_content_stream(
                model=self.model,
                contents=text,
                config=config,
            )

        for chunk in stream:

            if chunk.text:
                yield chunk.text

    def count_tokens(self, text: str) -> int:

        if not text:
            return 0

        result = self.client.models.count_tokens(
            model=self.model,
            contents=text,
        )

        return result.total_tokens

    def remaining_input_tokens(self, text: str) -> int:

        used = self.count_tokens(text)

        return max(
            0,
            self.input_token_limit - used,
        )

    def reset(self) -> None:
        self._chat = None

    @property
    def history(self):
        if self._chat is None:
            return []

        return list(self._chat.get_history())

    def _config_with_overrides(
        self,
        overrides: dict[str, Any],
    ) -> types.GenerateContentConfig:

        if not overrides:
            return self.config

        values = {
            "system_instruction": self.config.system_instruction,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "top_k": self.config.top_k,
            "max_output_tokens": self.config.max_output_tokens,
            "stop_sequences": self.config.stop_sequences,
        }

        values.update(overrides)

        return types.GenerateContentConfig(**values)
