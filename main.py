import argparse
import sys
import io
import json

# Force UTF-8 output on Windows to avoid cp1252 UnicodeEncodeError with special chars
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from pathlib import Path
import numpy as np
import soundfile as sf
from pydub import AudioSegment

from src.utils.config_loader import load_config
from src.utils.logger import get_logger, log_banner
from src.narration.kokoro_tts_engine import KokoroTTSEngine

log = get_logger("main")


def run_pipeline(args) -> None:
    log_banner("AI Cinematic Story Narrator (Kokoro Edition)")

    # 1. Load configuration
    config = load_config(args.config)
    
    # Override paths if CLI arguments are provided
    if args.story:
        story_path = Path(args.story)
    else:
        story_path = Path(config["paths"]["input_stories"]) / "example_horror.txt"

    if not story_path.exists():
        # Fallback to check if .json version exists
        json_fallback = story_path.with_suffix(".json")
        if json_fallback.exists():
            story_path = json_fallback
        else:
            log.error(f"Story file not found: {story_path}")
            sys.exit(1)

    log.info(f"Loaded configuration: {args.config}")
    log.info(f"Target Story: {story_path}")

    # 2. Read and parse story
    is_json = story_path.suffix.lower() == ".json"
    scenes = []

    if is_json:
        log.info("Parsing structured JSON story...")
        try:
            with open(story_path, "r", encoding="utf-8") as f:
                story_data = json.load(f)
            
            title = story_data.get("title", "Untitled Story")
            log.info(f"Story Title: {title}")
            
            for idx, scene in enumerate(story_data.get("scenes", []), start=1):
                text = scene.get("text", "").strip()
                if not text:
                    continue
                scenes.append({
                    "text": text,
                    "voice": scene.get("voice"),
                    "speed": scene.get("speed"),
                    "pause_after": float(scene.get("pause_after", 0.8))
                })
        except Exception as e:
            log.error(f"Failed to parse JSON story: {e}")
            sys.exit(1)
    else:
        log.info("Parsing plain text story...")
        with open(story_path, "r", encoding="utf-8") as f:
            story_text = f.read()
        
        # Split by double newline to separate paragraphs
        paragraphs = [p.strip() for p in story_text.split("\n\n") if p.strip()]
        for para in paragraphs:
            scenes.append({
                "text": para,
                "voice": None,
                "speed": None,
                "pause_after": 0.8
            })

    log.info(f"Parsed story into {len(scenes)} narration segment(s).")

    # 3. Initialize TTS Engine
    tts_engine = KokoroTTSEngine(config)

    # 4. Generate audio per scene
    scene_files = []
    log_banner("Generating Narration")
    for idx, scene in enumerate(scenes, start=1):
        filename = f"scene_{idx:03d}.wav"
        text = scene["text"]
        voice = scene["voice"]
        speed = scene["speed"]
        pause_after = scene["pause_after"]
        
        try:
            log.info(f"\n--- Segment {idx}/{len(scenes)} ---")
            log.info(f"Text preview: \"{text[:60]}...\"")
            if voice:
                log.info(f"Voice override: {voice} | Speed override: {speed}")
            
            # Temporary override of engine speed if defined in scene
            old_speed = tts_engine.speed
            if speed is not None:
                tts_engine.speed = speed
            
            # Generate paragraph narration
            audio_path = tts_engine.generate_narration(text, filename, scene_id=idx, voice=voice)
            
            # Restore speed
            tts_engine.speed = old_speed
            
            scene_files.append({
                "path": audio_path,
                "pause_after": pause_after
            })
        except Exception as e:
            log.error(f"Failed to generate segment {idx}: {e}")
            sys.exit(1)

    # 5. Concatenate paragraphs into final master file
    log_banner("Assembling Final Master Narration")
    if not scene_files:
        log.error("No audio files were generated.")
        sys.exit(1)

    output_dir = Path(config["paths"]["output_audio"])
    output_dir.mkdir(parents=True, exist_ok=True)
    master_path = output_dir / "final_narration.wav"

    log.info("Concatenating audio segments...")
    combined_audio = []
    sample_rate = None

    for idx, item in enumerate(scene_files, start=1):
        filepath = item["path"]
        pause_after = item["pause_after"]
        
        data, sr = sf.read(str(filepath))
        if sample_rate is None:
            sample_rate = sr
        elif sr != sample_rate:
            log.warning(f"Sample rate mismatch: {sr} != {sample_rate}. Using sample rate {sample_rate}.")
        
        combined_audio.append(data)
        
        # Add pause after the segment (skip pause for the last segment if it is a clean end)
        if idx < len(scene_files):
            silence_len = int(sr * pause_after)
            if len(data.shape) > 1:
                # Stereo/multi-channel
                silence = np.zeros((silence_len, data.shape[1]), dtype=data.dtype)
            else:
                silence = np.zeros(silence_len, dtype=data.dtype)
            combined_audio.append(silence)

    if combined_audio:
        final_data = np.concatenate(combined_audio)

        # ── Export WAV ────────────────────────────────────────────────────
        sf.write(str(master_path), final_data, sample_rate)
        log.info(f"[bold green][OK] WAV saved:[/bold green] [cyan]{master_path}[/cyan]")

        # ── Export MP3 (320 kbps — highest quality) ───────────────────────
        mp3_path = master_path.with_suffix(".mp3")
        try:
            audio_segment = AudioSegment.from_wav(str(master_path))
            audio_segment.export(
                str(mp3_path),
                format="mp3",
                bitrate="320k",
                parameters=["-q:a", "0"],   # VBR quality 0 = best
            )
            log.info(f"[bold green][OK] MP3 saved:[/bold green]  [cyan]{mp3_path}[/cyan]")
        except Exception as e:
            log.warning(f"MP3 export failed (ffmpeg missing?): {e}")

        # ── Optional Cleanup of Temporary Scene Files ─────────────────────
        cleanup_cfg = config.get("cleanup", {})
        if cleanup_cfg.get("delete_temp_files", True):
            log.info("Cleaning up temporary audio segments...")
            for item in scene_files:
                try:
                    filepath = item["path"]
                    if filepath.exists():
                        filepath.unlink()
                except Exception as cleanup_err:
                    log.warning(f"Failed to delete temp file {item['path']}: {cleanup_err}")
            log.info("[OK] Temporary segment files deleted.")

        log.info("[bold green][DONE] All output files ready![/bold green]")
    else:
        log.error("Combined audio output is empty.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Cinematic Story Narrator (Kokoro)")
    parser.add_argument("--story", type=str, help="Path to story text or JSON file")
    parser.add_argument("--config", type=str, default="config/settings.yaml", help="Path to settings.yaml")
    args = parser.parse_args()
    
    run_pipeline(args)
