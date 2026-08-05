import subprocess
from pathlib import Path
from threading import Semaphore
from PIL import Image

try:
    import pillow_avif
except ImportError:
    pass


class MediaCompressor:

    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".avif",
        ".bmp",
        ".gif",
    }

    VIDEO_EXTENSIONS = {
        ".mp4",
        ".webm",
        ".mov",
        ".m4v",
        ".ogv",
    }

    # ffmpeg video encodes are CPU-heavy; bound how many run at once
    # regardless of how many sources/threads are calling compress()
    # concurrently, since this is shared across all MediaCompressor
    # instances in the process.
    VIDEO_WORKERS = 3
    _video_semaphore = Semaphore(VIDEO_WORKERS)

    def __init__(
        self,
        image_quality: int = 70,
        video_crf: int = 30,
        max_width: int = 1920,
    ):
        self.image_quality = image_quality
        self.video_crf = video_crf
        self.max_width = max_width

    def compress(self, file: str):

        path = Path(file)
        ext = path.suffix.lower()

        if ext in self.IMAGE_EXTENSIONS:
            self._compress_image(path)

        elif ext in self.VIDEO_EXTENSIONS:
            with self._video_semaphore:
                self._compress_video(path)

        return str(path)

    def extract_video_thumbnail(self, video_file: str, thumb_file: str):
        video_path = Path(video_file)
        thumb_path = Path(thumb_file)

        thumb_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-ss",
            "0",
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(thumb_path),
        ]

        with self._video_semaphore:
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

        self._compress_image(thumb_path)

        return str(thumb_path)

    def _compress_image(self, path: Path):

        img = Image.open(path)

        img.info.clear()

        if img.width > self.max_width:
            ratio = self.max_width / img.width
            img = img.resize(
                (
                    self.max_width,
                    int(img.height * ratio)
                ),
                Image.Resampling.LANCZOS
            )

        ext = path.suffix.lower()

        if ext in {".jpg", ".jpeg"}:
            img.convert("RGB").save(
                path,
                "JPEG",
                quality=self.image_quality,
                optimize=True,
                progressive=True,
            )

        elif ext == ".png":
            img.save(
                path,
                "PNG",
                optimize=True,
                compress_level=9,
            )

        elif ext == ".webp":
            img.save(
                path,
                "WEBP",
                quality=self.image_quality,
                method=6,
            )

        elif ext == ".avif":
            img.save(
                path,
                "AVIF",
                quality=self.image_quality,
            )


    def _compress_video(self, path: Path):

        temp = path.with_name(
            path.stem + "_compressed" + path.suffix
        )

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(path),

            "-map_metadata",
            "-1",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-threads",
            "1",

            "-crf",
            str(self.video_crf),

            "-c:a",
            "aac",

            "-b:a",
            "96k",

            str(temp),
        ]

        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        temp.replace(path)