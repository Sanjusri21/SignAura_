import asyncio
import logging
import os
import shutil
import subprocess
from typing import Optional

logger = logging.getLogger("signaura.video.ffmpeg")


class FFmpegError(RuntimeError):
    """Raised when FFmpeg cannot extract audio."""


class FFmpegProcessor:
    """Extract real 16 kHz mono PCM WAV audio using FFmpeg."""

    @staticmethod
    def _get_ffmpeg_binary() -> str:
        """
        Locate FFmpeg.

        Priority:
        1. FFmpeg available in system PATH
        2. imageio-ffmpeg bundled executable
        """

        # ---------------------------------------------------------
        # 1. Check normal system PATH
        # ---------------------------------------------------------

        system_ffmpeg = shutil.which("ffmpeg")

        if system_ffmpeg:
            logger.info(
                "Using system FFmpeg: %s",
                system_ffmpeg,
            )
            return system_ffmpeg

        # ---------------------------------------------------------
        # 2. Check imageio-ffmpeg
        # ---------------------------------------------------------

        try:
            import imageio_ffmpeg

            binary = imageio_ffmpeg.get_ffmpeg_exe()

            if binary and os.path.isfile(binary):
                logger.info(
                    "Using imageio-ffmpeg: %s",
                    binary,
                )

                # Add FFmpeg directory to PATH so other libraries
                # such as Whisper can find it too.
                ffmpeg_dir = os.path.dirname(binary)

                current_path = os.environ.get("PATH", "")

                if ffmpeg_dir not in current_path.split(
                    os.pathsep
                ):
                    os.environ["PATH"] = (
                        ffmpeg_dir
                        + os.pathsep
                        + current_path
                    )

                return binary

        except Exception as exc:
            logger.warning(
                "imageio-ffmpeg lookup failed: %s",
                exc,
            )

        raise FFmpegError(
            "FFmpeg could not be located. "
            "Install imageio-ffmpeg using: "
            "pip install imageio-ffmpeg"
        )

    @classmethod
    async def extract_audio(
        cls,
        video_path: str,
        output_wav_path: Optional[str] = None,
    ) -> str:

        # ---------------------------------------------------------
        # Validate input
        # ---------------------------------------------------------

        if not video_path:
            raise FFmpegError(
                "No input media path was provided."
            )

        video_path = os.path.abspath(video_path)

        if not os.path.isfile(video_path):
            raise FFmpegError(
                f"Input media file does not exist:\n{video_path}"
            )

        if os.path.getsize(video_path) == 0:
            raise FFmpegError(
                f"Input media file is empty:\n{video_path}"
            )

        logger.info(
            "FFmpeg input: %s",
            video_path,
        )

        # ---------------------------------------------------------
        # Create output WAV path
        # ---------------------------------------------------------

        if not output_wav_path:
            base_name, _ = os.path.splitext(video_path)

            output_wav_path = (
                f"{base_name}_audio.wav"
            )

        output_wav_path = os.path.abspath(
            output_wav_path
        )

        output_dir = os.path.dirname(
            output_wav_path
        )

        if output_dir:
            os.makedirs(
                output_dir,
                exist_ok=True,
            )

        # ---------------------------------------------------------
        # Remove old output if it exists
        # ---------------------------------------------------------

        if os.path.isfile(output_wav_path):
            try:
                os.remove(output_wav_path)
            except OSError as exc:
                raise FFmpegError(
                    f"Cannot overwrite existing WAV file: "
                    f"{output_wav_path}"
                ) from exc

        # ---------------------------------------------------------
        # Find FFmpeg
        # ---------------------------------------------------------

        ffmpeg_bin = cls._get_ffmpeg_binary()

        logger.info(
            "Using FFmpeg binary: %s",
            ffmpeg_bin,
        )

        # ---------------------------------------------------------
        # FFmpeg command
        # ---------------------------------------------------------

        cmd = [
            ffmpeg_bin,

            # Do not show unnecessary FFmpeg banner.
            "-hide_banner",

            # Only show errors.
            "-loglevel",
            "error",

            # Automatically overwrite output.
            "-y",

            # Input video/audio.
            "-i",
            video_path,

            # Remove video stream.
            "-vn",

            # PCM 16-bit WAV.
            "-acodec",
            "pcm_s16le",

            # Whisper-friendly sample rate.
            "-ar",
            "16000",

            # Mono audio.
            "-ac",
            "1",

            # Prevent FFmpeg from waiting for terminal input.
            "-nostdin",

            output_wav_path,
        ]

        logger.info(
            "Running FFmpeg audio extraction..."
        )

        loop = asyncio.get_running_loop()

        def _run() -> str:

            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                    timeout=600,
                )

            except subprocess.TimeoutExpired as exc:

                logger.error(
                    "FFmpeg timed out."
                )

                raise FFmpegError(
                    "FFmpeg audio extraction timed out "
                    "after 10 minutes."
                ) from exc

            except subprocess.CalledProcessError as exc:

                error = (
                    exc.stderr or ""
                ).strip()

                logger.error(
                    "FFmpeg failed: %s",
                    error,
                )

                raise FFmpegError(
                    "FFmpeg audio extraction failed: "
                    f"{error or 'unknown error'}"
                ) from exc

            except OSError as exc:

                logger.error(
                    "Could not start FFmpeg: %s",
                    exc,
                )

                raise FFmpegError(
                    f"Could not start FFmpeg: {exc}"
                ) from exc

            # -----------------------------------------------------
            # Validate generated WAV
            # -----------------------------------------------------

            if not os.path.isfile(
                output_wav_path
            ):
                raise FFmpegError(
                    "FFmpeg completed but did not "
                    "create the WAV file."
                )

            file_size = os.path.getsize(
                output_wav_path
            )

            if file_size < 100:
                raise FFmpegError(
                    "FFmpeg produced an invalid or "
                    "empty WAV audio file."
                )

            logger.info(
                "Audio extraction successful."
            )

            logger.info(
                "WAV file: %s",
                output_wav_path,
            )

            logger.info(
                "WAV size: %.2f MB",
                file_size / (1024 * 1024),
            )

            return output_wav_path

        return await loop.run_in_executor(
            None,
            _run,
        )


ffmpeg_processor = FFmpegProcessor()