import hashlib


class IDGenerator:

    @staticmethod
    def generate(text: str) -> str:
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return f"{text_hash[:12]}"