"""
Chatterbox-Bangla Voice Cloning Engine for CineAudio.
Performs expressive zero-shot voice cloning in Bengali using BosonLab/chatterbox-bangla.
"""

import os
import sys
from pathlib import Path
from typing import Optional
import torch
import torchaudio
from huggingface_hub import snapshot_download

from src.utils.logger import get_logger

log = get_logger("chatterbox_engine")


class ChatterboxBanglaEngine:
    def __init__(self, config: dict):
        self.config = config
        self.tts_cfg = config.get("tts", {})
        self.paths_cfg = config.get("paths", {})

        self.device = self.tts_cfg.get("device", "cuda" if torch.cuda.is_available() else "cpu")
        self.speed = float(self.tts_cfg.get("speed", 1.0))
        self.temp_dir = Path(self.paths_cfg.get("temp_dir", "output/.tmp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        ref_voice_path = self.tts_cfg.get("clone_ref_audio", "input/voices/reference_voice_24k.wav")
        self.ref_audio_path = Path(ref_voice_path)
        if not self.ref_audio_path.exists():
            alt_ref = Path("input/voices/reference_voice_sample.wav")
            raw_vocals = Path("input/voices/audio [vocals].mp3")
            if alt_ref.exists():
                self.ref_audio_path = alt_ref
            elif raw_vocals.exists():
                self.ref_audio_path = raw_vocals

        # Ensure chatterbox-finetuning src directory is accessible without colliding with project 'src'
        finetuning_src = Path(__file__).resolve().parent.parent / "chatterbox_finetuning" / "src"
        if str(finetuning_src) not in sys.path:
            sys.path.insert(0, str(finetuning_src))

        log.info(f"Loading Chatterbox-Bangla model (BosonLab/chatterbox-bangla) onto [bold cyan]{self.device}[/bold cyan]...")
        model_dir = snapshot_download("BosonLab/chatterbox-bangla")

        from chatterbox_.tts import ChatterboxTTS
        self.model = ChatterboxTTS.from_local(model_dir, device=self.device)
        self.sample_rate = self.model.sr
        log.info(f"[bold green]Chatterbox-Bangla Engine Ready![/bold green] (Sample rate: {self.sample_rate}Hz)")

    def generate_narration(
        self,
        text: str,
        filename: str,
        scene_id: Optional[int] = None,
        voice: Optional[str] = None
    ) -> Path:
        """
        Synthesize speech with voice cloning from reference vocal.
        """
        out_path = self.temp_dir / filename
        log.info(f"Synthesizing Bangla audio with Chatterbox: '{text[:50]}...'")

        ref_file = str(self.ref_audio_path)
        if voice and Path(voice).exists():
            ref_file = str(voice)

        # Generate audio using reference voice prompt
        # Lower exaggeration and temperature reduces theatrical West Bengal intonation
        # Higher repetition_penalty prevents trailing consonant artifacts (like trailing "ত")
        wav = self.model.generate(
            text,
            audio_prompt_path=ref_file,
            exaggeration=0.35,
            repetition_penalty=1.3,
            temperature=0.6,
            cfg_weight=0.6
        )
        
        # Ensure 2D tensor [channels, samples] for torchaudio save
        if wav.dim() == 1:
            wav = wav.unsqueeze(0)

        torchaudio.save(str(out_path), wav.cpu(), self.sample_rate)
        return out_path
