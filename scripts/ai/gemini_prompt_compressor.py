import html
import re
import unicodedata
from functools import lru_cache

from parsivar import Normalizer
from llmlingua import PromptCompressor


class GeminiPromptCompressor:

    MODEL_NAME = (
        "microsoft/"
        "llmlingua-2-xlm-roberta-large-meetingbank"
    )

    def __init__(
        self,
        max_tokens: int,
        device: str = "cpu",
    ):
        if max_tokens < 1:
            raise ValueError(
                "max_tokens must be greater than 0"
            )

        self.max_tokens = max_tokens
        self.normalizer = Normalizer()

        self.compressor = PromptCompressor(
            model_name=self.MODEL_NAME,
            device_map=device,
            use_llmlingua2=True,
            llmlingua2_config={
                "max_batch_size": 32,
                "max_force_token": 100,
            },
        )

    def clean(self, text: str) -> str:

        if not text:
            return ""

        text = html.unescape(str(text))

        text = re.sub(
            r"https?://\S+|www\.\S+",
            " ",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"@\w+",
            " ",
            text,
        )

        text = re.sub(
            r"[\u200b\u200c\u200d\ufeff]",
            "",
            text,
        )

        text = re.sub(
            r"\b(?:rlm|lrm|amp|nbsp|quot)\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )

        text = "".join(
            char
            for char in text
            if unicodedata.category(char)
            not in {"So", "Sk"}
        )

        text = re.sub(
            r"[•‣⁃∙·]+",
            " ",
            text,
        )

        text = re.sub(
            r"[,.]{2,}",
            ".",
            text,
        )

        try:
            text = self.normalizer.normalize(text)
        except Exception:
            pass

        text = re.sub(
            r"[ \t\u00a0]+",
            " ",
            text,
        )

        text = re.sub(
            r"[ \t]*\n[ \t]*",
            "\n",
            text,
        )

        text = re.sub(
            r"\n{2,}",
            "\n",
            text,
        )

        return text.strip()

    @staticmethod
    @lru_cache(maxsize=32768)
    def _fingerprint(text: str) -> str:

        text = text.lower()

        text = re.sub(
            r"[^\w\u0600-\u06ff]",
            " ",
            text,
        )

        return " ".join(text.split())

    def _deduplicate_sentences(
        self,
        text: str,
    ) -> str:

        sentences = re.split(
            r"(?<=[.!؟])\s+|\n+",
            text,
        )

        seen = set()
        result = []

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            fingerprint = self._fingerprint(
                sentence
            )

            if not fingerprint:
                continue

            if fingerprint in seen:
                continue

            seen.add(fingerprint)
            result.append(sentence)

        return "\n".join(result)

    def _compress_llmlingua(
        self,
        text: str,
    ) -> str:

        result = self.compressor.compress_prompt(
            text,
            target_token=self.max_tokens,
            use_context_level_filter=False,
            use_token_level_filter=True,
            force_tokens=[
                "\n",
                ".",
                "؟",
                "!",
                ":",
                "؛",
            ],
            force_reserve_digit=True,
            keep_first_sentence=1,
            keep_last_sentence=1,
            reorder_context="original",
            strict_preserve_uncompressed=True,
        )

        return result[
            "compressed_prompt"
        ].strip()

    def compress(
        self,
        text: str,
        token_counter=None,
    ) -> str:

        text = self.clean(text)

        if not text:
            return ""

        text = self._deduplicate_sentences(
            text
        )

        if not text:
            return ""

        if token_counter is not None:

            if (
                token_counter(text)
                <= self.max_tokens
            ):
                return text

        compressed = self._compress_llmlingua(
            text
        )

        if not compressed:
            return ""

        if token_counter is None:
            return compressed

        actual_tokens = token_counter(
            compressed
        )

        if actual_tokens <= self.max_tokens:
            return compressed

        return self._recompress(
            text,
            token_counter,
        )

    def _recompress(
        self,
        text: str,
        token_counter,
    ) -> str:

        target = self.max_tokens

        for _ in range(3):

            compressed = self.compressor.compress_prompt(
                text,
                target_token=target,
                use_context_level_filter=False,
                use_token_level_filter=True,
                force_tokens=[
                    "\n",
                    ".",
                    "؟",
                    "!",
                    ":",
                    "؛",
                ],
                force_reserve_digit=True,
                keep_first_sentence=1,
                keep_last_sentence=1,
                reorder_context="original",
                strict_preserve_uncompressed=True,
            )[
                "compressed_prompt"
            ].strip()

            if not compressed:
                return ""

            actual_tokens = token_counter(
                compressed
            )

            if actual_tokens <= self.max_tokens:
                return compressed

            target = max(
                1,
                int(
                    target
                    * self.max_tokens
                    / actual_tokens
                    * 0.95
                ),
            )

        return self._hard_limit(
            compressed,
            token_counter,
        )

    def _hard_limit(
        self,
        text: str,
        token_counter,
    ) -> str:

        if token_counter(text) <= self.max_tokens:
            return text

        words = text.split()

        low = 1
        high = len(words)
        best = ""

        while low <= high:

            middle = (
                low + high
            ) // 2

            candidate = " ".join(
                words[:middle]
            )

            if (
                token_counter(candidate)
                <= self.max_tokens
            ):
                best = candidate
                low = middle + 1
            else:
                high = middle - 1

        return best.strip()

    def compress_items(
        self,
        items: list[str],
        token_counter=None,
    ) -> str:

        if not items:
            return ""

        cleaned = []

        for item in items:

            item = self.clean(item)

            if item:
                cleaned.append(item)

        if not cleaned:
            return ""

        return self.compress(
            "\n\n".join(cleaned),
            token_counter=token_counter,
        )
