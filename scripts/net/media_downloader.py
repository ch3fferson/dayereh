import time
import requests
import shutil
from pathlib import Path
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.path_utils import PathUtils
from converters.media_type import MediaType
from converters.media_compressor import MediaCompressor


class MediaDownloader:

    MAX_ATTEMPTS = 3
    BACKOFF_FACTOR = 1.0

    def __init__(self, storage:PathUtils):
        self.storage = storage

        self.session = self._build_session()

        self.compressor = MediaCompressor(
            image_quality=70,
            video_crf=30
        )

    def _build_session(self) -> requests.Session:
        session = requests.Session()

        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=False,
        )

        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=retry,
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def download(self, url: str, post_id: str):

            parsed = urlparse(url)

            ext = Path(parsed.path).suffix.lower()

            if not MediaType.is_supported_ext(ext):
                return None

            filename = f"{post_id.replace('/','_')}{ext}"

            destination = self.storage.media / filename

            last_error = None

            for attempt in range(self.MAX_ATTEMPTS):

                try:

                    with self.session.get(url, stream=True, timeout=20) as r:

                        r.raise_for_status()

                        with open(destination, "wb") as f:
                            shutil.copyfileobj(r.raw, f)

                    self.compressor.compress(
                        str(destination)
                    )

                    return f"{filename}"

                except Exception as e:
                    last_error = e
                    destination.unlink(missing_ok=True)

                    if attempt < self.MAX_ATTEMPTS - 1:
                        time.sleep(self.BACKOFF_FACTOR * (2 ** attempt))

            print(f"error: {last_error}")
            return None