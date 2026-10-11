"""
Edge-TTS Engine for high-quality multilingual narration,
supporting natural neural Bangla (bn-BD / bn-IN) voices without external dependencies.
"""

import asyncio
from pathlib import Path
import soundfile as sf

from src.utils.logger import get_logger

log = get_logger(__name__)


class EdgeTTSEngine:
    """
    Synthesizes speech using Microsoft Edge Neural TTS voices,
    providing high quality Bangla (and English/multilingual) speech.
    """

    def __init__(self, config: dict):
        self.config = config
        tts_cfg = config.get("tts", {})
        
        # Default voice for Bangla: bn-BD-PradeepNeural (Male) or bn-BD-NabanitaNeural (Female)
        self.voice = tts_cfg.get("voice", "bn-BD-PradeepNeural")
        self.speed = tts_cfg.get("speed", 1.0)
        self.pitch = tts_cfg.get("pitch", "+0Hz")
        self.volume = tts_cfg.get("volume", "+0%")

        self.output_dir = Path(config["paths"]["output_audio"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _convert_rate(self, speed_val: float) -> str:
        """
        Converts float speed (e.g. 0.9, 1.1) to Edge TTS rate string (e.g. "-10%", "+10%").
        """
        pct = int(round((speed_val - 1.0) * 100))
        if pct >= 0:
            return f"+{pct}%"
        return f"{pct}%"

    async def _synthesize_async(self, text: str, voice: str, rate: str, temp_mp3_path: Path):
        import edge_tts
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=self.pitch,
            volume=self.volume
        )
        await communicate.save(str(temp_mp3_path))

    def generate_narration(
        self,
        text: str,
        output_filename: str,
        scene_id: int | None = None,
        voice: str | None = None
    ) -> Path:
        """
        Synthesizes text to a WAV file matching the project pipeline requirements.
        """
        voice_to_use = voice or self.voice
        rate_to_use = self._convert_rate(self.speed)
        scene_lbl = f"Scene {scene_id}" if scene_id is not None else "Text"
        log.info(f"  [EdgeTTS] Generating narration for {scene_lbl} using '{voice_to_use}' (rate: {rate_to_use})...")

        out_path = self.output_dir / output_filename
        temp_mp3 = self.output_dir / f"temp_{out_path.stem}.mp3"

        try:
            # 1. Generate via edge-tts into temp MP3
            asyncio.run(self._synthesize_async(text, voice_to_use, rate_to_use, temp_mp3))

            # 2. Read MP3 data directly using libsndfile (soundfile) and write uncompressed WAV
            data, sr = sf.read(str(temp_mp3))
            sf.write(str(out_path), data, sr)

            # 3. Clean temporary MP3
            if temp_mp3.exists():
                temp_mp3.unlink()

            log.info(f"    [OK] Saved: {out_path.name}")
            return out_path

        except Exception as e:
            if temp_mp3.exists():
                temp_mp3.unlink()
            log.error(f"EdgeTTS synthesis failed: {e}")
            raise e
