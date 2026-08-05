import html
import re
import unicodedata
from functools import lru_cache

from parsivar import Normalizer


class GeminiPromptCompressor:

    IMPORTANT_PATTERNS = (
        r"\d",
        r"%",
        r"\b(?:۱۹|۲۰)\d{2}\b",
        r"\b(?:دلار|یورو|پوند|روبل|ریال|تومان)\b",
        r"\b(?:میلیون|میلیارد|هزار)\b",
        r"\b(?:امروز|دیروز|فردا|امشب|صبح|شب)\b",
        r"\b(?:ایران|آمریکا|اسرائیل|روسیه|اوکراین|چین|اروپا|"
        r"غزه|فلسطین|لبنان|سوریه|عراق|یمن|ترکیه|عربستان)\b",
        r"\b(?:ترامپ|پوتین|نتانیاهو|بایدن|زلنسکی|خامنه‌ای|"
        r"پزشکیان|مکرون|شی|پوتین)\b",
        r"\b(?:دولت|وزارت|ارتش|سپاه|مجلس|کاخ سفید|"
        r"سازمان ملل|ناتو|اتحادیه اروپا)\b",
        r"\b(?:حمله|جنگ|آتش‌بس|تحریم|مذاکره|توافق|"
        r"موشک|هسته‌ای|نظامی|امنیتی|انتخابات)\b",
        r"\b(?:اعلام کرد|گفت|افزود|تأکید کرد|تاکید کرد|"
        r"اظهار داشت|خبر داد|گزارش داد)\b",
    )

    def __init__(self, max_tokens: int):
        if max_tokens < 1:
            raise ValueError("max_tokens must be greater than 0")

        self.max_tokens = max_tokens
        self.normalizer = Normalizer()

        self._important_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.IMPORTANT_PATTERNS
        ]

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
            r'<[^>]+>|[{}\[\]":,]',
            ' ',
            text)

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
            if unicodedata.category(char) not in {"So", "Sk"}
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
    @lru_cache(maxsize=16384)
    def _fingerprint(text: str) -> str:

        text = text.lower()

        text = re.sub(
            r"[^\w\u0600-\u06ff]",
            " ",
            text,
        )

        return " ".join(text.split())

    def split_sentences(self, text: str) -> list[str]:

        return [
            sentence.strip()
            for sentence in re.split(
                r"(?<=[.!؟])\s+|\n+",
                text,
            )
            if sentence.strip()
        ]

    def deduplicate(self, sentences: list[str]) -> list[str]:

        seen = set()
        result = []

        for sentence in sentences:

            fingerprint = self._fingerprint(sentence)

            if not fingerprint or fingerprint in seen:
                continue

            seen.add(fingerprint)
            result.append(sentence)

        return result

    def _importance(self, sentence: str, index: int, total: int) -> float:

        words = sentence.split()
        word_count = len(words)

        if word_count < 3:
            return -100.0

        score = 0.0

        for pattern in self._important_patterns:

            matches = pattern.findall(sentence)

            if matches:
                score += min(len(matches), 3) * 3.0

        if word_count >= 8:
            score += 2.0

        if word_count >= 15:
            score += 2.0

        if word_count >= 30:
            score += 1.0

        if '"' in sentence or "«" in sentence or "»" in sentence:
            score += 2.0

        if re.search(r"[!?؟]", sentence):
            score += 0.5

        if index < max(3, total * 0.1):
            score += 1.5

        if index >= total * 0.9:
            score += 0.5

        return score

    @staticmethod
    def _estimate_tokens(text: str) -> int:

        if not text:
            return 0

        persian = len(
            re.findall(
                r"[\u0600-\u06ff]",
                text,
            )
        )

        latin = len(
            re.findall(
                r"[a-zA-Z]",
                text,
            )
        )

        digits = len(
            re.findall(
                r"\d",
                text,
            )
        )

        spaces = text.count(" ")

        estimated = (
            persian / 2.5
            + latin / 4
            + digits / 2
            + spaces / 3
        )

        return max(
            1,
            int(estimated),
        )

    def _select(
        self,
        sentences: list[str],
    ) -> list[str]:

        if not sentences:
            return []

        if self._estimate_tokens(" ".join(sentences)) <= self.max_tokens:
            return sentences

        total = len(sentences)

        ranked = sorted(
            (
                (
                    self._importance(
                        sentence,
                        index,
                        total,
                    ),
                    index,
                    sentence,
                    self._estimate_tokens(sentence),
                )
                for index, sentence in enumerate(sentences)
            ),
            key=lambda item: (
                item[0],
                -item[3],
            ),
            reverse=True,
        )

        selected = []
        used_tokens = 0

        for _, index, sentence, tokens in ranked:

            if used_tokens + tokens > self.max_tokens:
                continue

            selected.append(
                (
                    index,
                    sentence,
                )
            )

            used_tokens += tokens

        selected.sort(
            key=lambda item: item[0],
        )

        return [
            sentence
            for _, sentence in selected
        ]

    def _fit_exact(
        self,
        sentences: list[str],
        token_counter,
    ) -> str:

        if not sentences:
            return ""

        text = " ".join(sentences)

        if token_counter(text) <= self.max_tokens:
            return text

        low = 0
        high = len(sentences)

        best = ""

        while low <= high:

            middle = (low + high) // 2

            candidate = " ".join(
                sentences[:middle]
            )

            if token_counter(candidate) <= self.max_tokens:

                best = candidate
                low = middle + 1

            else:

                high = middle - 1

        if best:
            return best

        return self._hard_limit(
            text,
            token_counter,
        )

    def _hard_limit(
        self,
        text: str,
        token_counter,
    ) -> str:

        if not text:
            return ""

        words = text.split()

        low = 0
        high = len(words)

        best = ""

        while low <= high:

            middle = (low + high) // 2

            candidate = " ".join(
                words[:middle]
            )

            if not candidate:
                low = middle + 1
                continue

            if token_counter(candidate) <= self.max_tokens:

                best = candidate
                low = middle + 1

            else:

                high = middle - 1

        return best.strip()

    def compress(
        self,
        text: str,
        token_counter=None,
    ) -> str:

        text = self.clean(text)

        if not text:
            return ""

        sentences = self.split_sentences(text)
        sentences = self.deduplicate(sentences)

        if not sentences:
            return ""

        estimated_tokens = self._estimate_tokens(text)

        if estimated_tokens <= self.max_tokens:

            if token_counter is None:
                return text

            if token_counter(text) <= self.max_tokens:
                return text

        selected = self._select(sentences)

        if not selected:
            return ""

        result = " ".join(selected)

        if token_counter is None:
            return result

        actual_tokens = token_counter(result)

        if actual_tokens <= self.max_tokens:
            return result

        return self._fit_exact(
            selected,
            token_counter,
        )

    def compress_items(
        self,
        items: list[str],
        token_counter=None,
    ) -> str:

        if not items:
            return ""

        cleaned_items = []

        for item in items:

            cleaned = self.clean(item)

            if cleaned:
                cleaned_items.append(cleaned)

        if not cleaned_items:
            return ""

        text = "\n".join(cleaned_items)

        return self.compress(
            text,
            token_counter=token_counter,
        )
