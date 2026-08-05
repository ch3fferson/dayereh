import re
import html


class StringUtils:

    @staticmethod
    def safe(value):

        if value is None:
            return ""

        return str(value).strip()
    
    @staticmethod
    def truncate_text_word(text, word_limit):

        if not text:
            return ""

        words = text.split()

        if len(words) <= word_limit:
            return text

        return " ".join(words[:word_limit]) + "..."
    
    @staticmethod
    def truncate_text_char(text, char_limit):

        if not text:
            return ""

        if len(text) <= char_limit:
            return text

        return text[:char_limit].rstrip() + "..."
    
    @staticmethod
    def remove_html_shenanigans(text):

        if not text:
            return ""

        text = html.unescape(text)
        text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]*>", " ", text)
        text = re.sub(r'"', " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()
    
    @staticmethod
    def detect_lang(text: str) -> str:
        text = text.lower()

        if re.search(r'[\u0600-\u06FF]', text):
            return "fa"
        elif re.search(r'[a-z]', text):
            return "en"

        return None