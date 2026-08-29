import asyncio
import logging
import os
import re
import uuid
from typing import Any, Dict, Optional

import yt_dlp

from app.core.config import settings

logger = logging.getLogger("signaura.video.downloader")


class VideoDownloadError(RuntimeError):
    """Raised when yt-dlp cannot download the requested media."""


class VideoDownloader:
    """Download actual YouTube media for the SignAura ASR pipeline."""

    @staticmethod
    def extract_youtube_id(url: str) -> Optional[str]:
        patterns = [
            r"(?:v=)([0-9A-Za-z_-]{11})",
            r"(?:youtu\.be/)([0-9A-Za-z_-]{11})",
            r"(?:youtube\.com/(?:embed|shorts)/)([0-9A-Za-z_-]{11})",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    @staticmethod
    def _safe_filename(value: str) -> str:
        """Make filename safe for Windows."""
        value = re.sub(r'[<>:"/\\|?*]', "_", value)
        value = re.sub(r"\s+", "_", value)
        return value[:100]

    async def download_media(
        self,
        url: str,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:

        if not url or not url.strip():
            raise VideoDownloadError(
                "A YouTube/media URL is required."
            )

        url = url.strip()

        # Validate YouTube URL
        youtube_id = self.extract_youtube_id(url)

        if not youtube_id:
            raise VideoDownloadError(
                "Invalid YouTube URL. Please provide a valid YouTube video URL."
            )

        out_dir = output_dir or settings.UPLOADS_DIR

        os.makedirs(out_dir, exist_ok=True)

        file_id = uuid.uuid4().hex

        # IMPORTANT:
        # Use only the UUID as filename.
        # This avoids Windows filename/path problems.
        output_template = os.path.join(
            out_dir,
            f"{file_id}.%(ext)s"
        )

        ydl_opts = {
            # Prefer m4a because Whisper/FFmpeg can process it reliably.
            "format": "bestaudio[ext=m4a]/bestaudio/best",

            "outtmpl": output_template,

            "noplaylist": True,

            # Windows-safe filenames
            "windowsfilenames": True,
            "restrictfilenames": True,

            # Do not download thumbnails/playlists/etc.
            "writethumbnail": False,
            "writesubtitles": False,
            "writeautomaticsub": False,

            # Network settings
            "socket_timeout": 60,
            "retries": 5,
            "fragment_retries": 5,

            # Avoid unnecessary console output
            "quiet": False,
            "no_warnings": False,

            # Do not use browser cookies
            "nocheckcertificate": True,

            # Explicitly allow IPv4
            "source_address": "0.0.0.0",

            # Avoid playlist processing
            "extract_flat": False,
        }

        loop = asyncio.get_running_loop()

        def _download() -> Dict[str, Any]:

            try:
                logger.info("Starting YouTube download: %s", url)

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                    info = ydl.extract_info(
                        url,
                        download=True
                    )

                    if not info:
                        raise VideoDownloadError(
                            "yt-dlp returned no video information."
                        )

                    logger.info(
                        "YouTube information extracted: %s",
                        info.get("title")
                    )

                    # Find the actual downloaded file.
                    requested_ext = info.get("ext")

                    possible_files = []

                    if requested_ext:
                        possible_files.append(
                            os.path.join(
                                out_dir,
                                f"{file_id}.{requested_ext}"
                            )
                        )

                    # Search for anything downloaded with our UUID.
                    if os.path.isdir(out_dir):
                        for filename in os.listdir(out_dir):

                            if filename.startswith(file_id + "."):

                                full_path = os.path.join(
                                    out_dir,
                                    filename
                                )

                                if os.path.isfile(full_path):
                                    possible_files.append(full_path)

                    downloaded_file = None

                    for candidate in possible_files:

                        if os.path.isfile(candidate):

                            if os.path.getsize(candidate) > 0:
                                downloaded_file = candidate
                                break

                    if not downloaded_file:
                        raise VideoDownloadError(
                            "yt-dlp completed but the downloaded audio file "
                            "could not be found."
                        )

                    logger.info(
                        "Downloaded media: %s",
                        downloaded_file
                    )

                    return {
                        "title": info.get("title") or "Online Video",
                        "duration": float(
                            info.get("duration") or 0.0
                        ),
                        "file_path": downloaded_file,
                        "thumbnail": info.get("thumbnail") or "",
                        "id": file_id,
                        "transcript": None,
                        "youtube_id": youtube_id,
                    }

            except VideoDownloadError:
                raise

            except Exception as exc:

                logger.exception(
                    "yt-dlp download failed"
                )

                raise VideoDownloadError(
                    f"YouTube download failed: {type(exc).__name__}: {exc}"
                ) from exc

        return await loop.run_in_executor(
            None,
            _download
        )


video_downloader = VideoDownloader()