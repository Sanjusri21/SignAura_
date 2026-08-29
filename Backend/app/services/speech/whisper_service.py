import asyncio
import logging
import os
import shutil
from typing import Any, Dict

from app.core.config import settings

logger = logging.getLogger("signaura.speech.whisper")


class WhisperTranscriptionError(RuntimeError):
    """Raised when real speech transcription cannot be completed."""


class WhisperSpeechTranscriber:
    """Local Whisper ASR using imageio-ffmpeg on Windows."""

    def __init__(self):
        self.model = None
        self._model_name = settings.WHISPER_MODEL

        # Configure FFmpeg immediately when the service starts.
        self._configure_ffmpeg()

    def _configure_ffmpeg(self):
        """Configure imageio-ffmpeg so OpenAI Whisper can find ffmpeg."""

        try:
            import imageio_ffmpeg

            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

            if not os.path.isfile(ffmpeg_path):
                raise WhisperTranscriptionError(
                    f"FFmpeg executable not found: {ffmpeg_path}"
                )

            ffmpeg_dir = os.path.dirname(ffmpeg_path)

            # Add FFmpeg directory to PATH.
            current_path = os.environ.get("PATH", "")

            path_entries = current_path.split(os.pathsep)

            if ffmpeg_dir not in path_entries:
                os.environ["PATH"] = (
                    ffmpeg_dir
                    + os.pathsep
                    + current_path
                )

            # Verify that the command "ffmpeg" can now be found.
            resolved_ffmpeg = shutil.which("ffmpeg")

            if not resolved_ffmpeg:
                raise WhisperTranscriptionError(
                    "FFmpeg executable exists, but Windows could not "
                    "resolve the 'ffmpeg' command."
                )

            logger.info(
                "FFmpeg configured successfully: %s",
                resolved_ffmpeg,
            )

        except ImportError as exc:
            raise WhisperTranscriptionError(
                "imageio-ffmpeg is not installed. Run:\n"
                "pip install imageio-ffmpeg"
            ) from exc

        except WhisperTranscriptionError:
            raise

        except Exception as exc:
            raise WhisperTranscriptionError(
                f"Could not configure FFmpeg: {exc}"
            ) from exc

    def _load_model(self):

        if self.model is None:

            try:
                import whisper

            except ImportError as exc:
                raise WhisperTranscriptionError(
                    "openai-whisper is not installed. Run:\n"
                    "pip install openai-whisper"
                ) from exc

            logger.info(
                "Loading Whisper model: %s",
                self._model_name,
            )

            self.model = whisper.load_model(
                self._model_name
            )

            logger.info("Whisper model loaded.")

        return self.model

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
    ) -> Dict[str, Any]:

        # ---------------------------------------------------------
        # Validate audio
        # ---------------------------------------------------------

        if not audio_path or not os.path.isfile(audio_path):

            raise WhisperTranscriptionError(
                f"Audio file does not exist: {audio_path}"
            )

        file_size = os.path.getsize(audio_path)

        if file_size < 100:

            raise WhisperTranscriptionError(
                f"Audio file is empty or invalid: {audio_path}"
            )

        # Make absolutely sure FFmpeg is available.
        self._configure_ffmpeg()

        logger.info(
            "Audio file: %s",
            audio_path,
        )

        logger.info(
            "Audio size: %d bytes",
            file_size,
        )

        loop = asyncio.get_running_loop()

        def _run_transcription() -> Dict[str, Any]:

            model = self._load_model()

            kwargs: Dict[str, Any] = {
                "fp16": False,
                "verbose": False,
            }

            # None = automatic language detection.
            if language:
                kwargs["language"] = language

            logger.info(
                "Starting Whisper transcription: %s",
                audio_path,
            )

            try:

                result = model.transcribe(
                    audio_path,
                    **kwargs,
                )

            except Exception as exc:

                logger.exception(
                    "Whisper failed: %s",
                    exc,
                )

                raise WhisperTranscriptionError(
                    f"Whisper transcription failed: {exc}"
                ) from exc

            # -----------------------------------------------------
            # Transcript
            # -----------------------------------------------------

            text = (
                result.get("text") or ""
            ).strip()

            if not text:

                raise WhisperTranscriptionError(
                    "Whisper completed but detected no speech."
                )

            # -----------------------------------------------------
            # Segments
            # -----------------------------------------------------

            segments = (
                result.get("segments") or []
            )

            duration = 0.0

            if segments:

                duration = max(
                    float(
                        segment.get(
                            "end",
                            0.0,
                        )
                    )
                    for segment in segments
                )

            # -----------------------------------------------------
            # Language
            # -----------------------------------------------------

            detected_language = (
                result.get("language")
                or language
                or "unknown"
            )

            logger.info(
                "Whisper completed successfully."
            )

            logger.info(
                "Language: %s",
                detected_language,
            )

            logger.info(
                "Duration: %.2f seconds",
                duration,
            )

            logger.info(
                "Transcript: %s",
                text,
            )

            # -----------------------------------------------------
            # Return
            # -----------------------------------------------------

            return {
                "text": text,
                "language": detected_language,
                "duration": duration,
                "segments": segments,
            }

        return await loop.run_in_executor(
            None,
            _run_transcription,
        )


whisper_service = WhisperSpeechTranscriber()