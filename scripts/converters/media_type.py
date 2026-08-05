from urllib.parse import urlparse


class MediaType:
    IMAGE_EXTENSIONS = frozenset({
        ".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp", ".svg"
    })

    GIF_EXTENSIONS = frozenset({
        ".gif"
    })

    VIDEO_EXTENSIONS = frozenset({
        ".mp4", ".webm", ".mov", ".m4v", ".ogv"
    })

    SUPPORTED_EXTENSIONS = (
        IMAGE_EXTENSIONS
        | GIF_EXTENSIONS
        | VIDEO_EXTENSIONS
    )

    TYPES = {
        **dict.fromkeys(IMAGE_EXTENSIONS, "image"),
        **dict.fromkeys(GIF_EXTENSIONS, "gif"),
        **dict.fromkeys(VIDEO_EXTENSIONS, "video"),
    }

    @staticmethod
    def _normalize_ext(ext: str) -> str:
        return f".{str(ext).lower().lstrip('.')}"

    @classmethod
    def detect_media_type_ext(cls, ext: str) -> str:
        media_type = cls.TYPES.get(cls._normalize_ext(ext))

        if media_type is None:
            raise ValueError(f"Unsupported media type: {ext}")

        return media_type

    @classmethod
    def detect_media_type_url(cls, url: str) -> str:
        path = urlparse(str(url)).path
        ext = path.rsplit(".", 1)[-1] if "." in path else ""

        return cls.detect_media_type_ext(ext)

    @classmethod
    def is_supported_ext(cls, ext: str) -> bool:
        return cls._normalize_ext(ext) in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def is_supported_url(cls, url: str) -> bool:
        path = urlparse(str(url)).path
        ext = path.rsplit(".", 1)[-1] if "." in path else ""

        return cls.is_supported_ext(ext)