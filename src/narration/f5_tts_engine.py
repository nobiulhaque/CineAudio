"""
F5-TTS Voice Cloning Engine for CineAudio.
Performs high-fidelity zero-shot voice cloning from a reference vocal audio track.
"""

import os
import sys
import io
import re
from pathlib import Path
from typing import Optional
import numpy as np
import soundfile as sf

# Ensure static-ffmpeg is available in PATH for audio decoding
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass

import torch
from f5_tts.api import F5TTS

from src.utils.logger import get_logger

log = get_logger("f5_tts_engine")


class F5TTSCloningEngine:
    def __init__(self, config: dict):
        self.config = config
        self.tts_cfg = config.get("tts", {})
        self.paths_cfg = config.get("paths", {})

        # Set environment variables for safety & quiet warnings
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        os.environ["PYTHONIOENCODING"] = "utf-8"

        self.device = self.tts_cfg.get("device", "cuda" if torch.cuda.is_available() else "cpu")
        self.speed = float(self.tts_cfg.get("speed", 1.0))
        self.temp_dir = Path(self.paths_cfg.get("temp_dir", "output/.tmp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Reference audio setup
        ref_voice_path = self.tts_cfg.get("clone_ref_audio", "input/voices/reference_voice_24k.wav")
        self.ref_audio_path = Path(ref_voice_path)
        if not self.ref_audio_path.exists():
            # Fallback to standard reference sample or raw vocals
            alt_ref = Path("input/voices/reference_voice_sample.wav")
            raw_vocals = Path("input/voices/audio [vocals].mp3")
            if alt_ref.exists():
                self.ref_audio_path = alt_ref
            elif raw_vocals.exists():
                self.ref_audio_path = raw_vocals
            else:
                log.warning(f"Reference voice audio file not found at: {self.ref_audio_path}")

        self.ref_text = self.tts_cfg.get("clone_ref_text", "")

        log.info(f"Initializing F5-TTS Engine on device: [bold cyan]{self.device}[/bold cyan]")
        log.info(f"Using Reference Vocal: [cyan]{self.ref_audio_path}[/cyan]")

        self.model = F5TTS(device=self.device)
        self.sample_rate = 24000
        log.info("[bold green]F5-TTS Voice Cloning Engine Ready![/bold green]")

    def generate_narration(
        self,
        text: str,
        filename: str,
        scene_id: Optional[int] = None,
        voice: Optional[str] = None
    ) -> Path:
        """
        Generate cloned voice narration for a given text segment.
        """
        out_path = self.temp_dir / filename
        log.info(f"Synthesizing cloned audio for: '{text[:50]}...'")

        ref_file = str(self.ref_audio_path)
        if voice and Path(voice).exists():
            ref_file = str(voice)

        # Call F5-TTS inference
        wav, sr, _ = self.model.infer(
            ref_file=ref_file,
            ref_text=self.ref_text,
            gen_text=text,
            file_wave=str(out_path),
            speed=self.speed
        )
        self.sample_rate = sr
        return out_path
