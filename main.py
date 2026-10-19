import argparse
import sys
import io
import json
import re

# Force UTF-8 output on Windows to avoid cp1252 UnicodeEncodeError with special chars
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from pathlib import Path
import numpy as np
import soundfile as sf
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except Exception:
    HAS_PYDUB = False

from src.utils.config_loader import load_config
from src.utils.logger import get_logger, log_banner

log = get_logger("main")


def format_timestamp(seconds, fmt_type="youtube"):
    seconds = int(round(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    
    if h > 0:
        time_str = f"{h:02d}:{m:02d}:{s:02d}"
    else:
        time_str = f"{m:02d}:{s:02d}"
        
    if fmt_type == "bracket":
        return f"[{time_str}]"
    return time_str



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

    # Extract timestamp settings
    ts_cfg = config.get("timestamps", {})
    ts_enabled = ts_cfg.get("enabled", True)
    ts_format = ts_cfg.get("format", "youtube")
    ts_suffix = ts_cfg.get("suffix", "_timestamps.txt")


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
                    "scene_title": scene.get("scene_title"),
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
            scene_title = None
            text_to_use = para
            if para.startswith("#"):
                parts = para.split("\n", 1)
                scene_title = parts[0].lstrip("# ").strip()
                text_to_use = parts[1].strip() if len(parts) > 1 else ""
            elif para.startswith("---") and "---" in para[3:]:
                parts = para.split("\n", 1)
                scene_title = parts[0].strip("- ")
                text_to_use = parts[1].strip() if len(parts) > 1 else ""
            
            if not text_to_use and scene_title:
                text_to_use = para
                
            scenes.append({
                "scene_title": scene_title,
                "text": text_to_use,
                "voice": None,
                "speed": None,
                "pause_after": 0.8
            })


    log.info(f"Loaded {len(scenes)} raw segments.")

    # Smart Flow Aggregation: Group tiny fragments into natural 5-8 second spoken blocks
    # Prevents 1-2 second robotic stops and provides natural breathing room
    grouped_scenes = []
    current_group = []
    current_word_count = 0
    min_words_per_clip = 14  # roughly 5-7 seconds of natural speech in Bengali
    max_words_per_clip = 32  # roughly 10-12 seconds

    for sc in scenes:
        words = sc["text"].split()
        sc_len = len(words)
        
        # If adding this scene exceeds max_words and we already have a healthy block, flush
        if current_group and (current_word_count + sc_len > max_words_per_clip or (current_word_count >= min_words_per_clip and sc.get("pause_after", 0.8) >= 1.0)):
            merged_text = " ".join([s["text"] for s in current_group])
            last_pause = current_group[-1].get("pause_after", 0.7)
            # Ensure dramatic pause between narrative blocks is smooth (0.6 - 0.8s)
            chosen_pause = max(0.5, min(last_pause, 1.0))
            grouped_scenes.append({
                "scene_title": current_group[0].get("scene_title"),
                "text": merged_text,
                "voice": current_group[0].get("voice"),
                "speed": current_group[0].get("speed"),
                "pause_after": chosen_pause
            })
            current_group = []
            current_word_count = 0

        current_group.append(sc)
        current_word_count += sc_len

    if current_group:
        merged_text = " ".join([s["text"] for s in current_group])
        grouped_scenes.append({
            "scene_title": current_group[0].get("scene_title"),
            "text": merged_text,
            "voice": current_group[0].get("voice"),
            "speed": current_group[0].get("speed"),
            "pause_after": current_group[-1].get("pause_after", 0.8)
        })

    scenes = grouped_scenes
    log.info(f"Aggregated story into {len(scenes)} natural narrative clip(s) (5-8s average breathing room).")

    # 3. Initialize TTS Engine
    tts_cfg = config.get("tts", {})
    engine_type = tts_cfg.get("engine", "").lower()
    default_voice = tts_cfg.get("voice", "")
    
    # Check if scene overrides or default voice indicates edge-tts (e.g. 'bn-BD', 'bn-IN', or 'Neural')
    first_voice = scenes[0].get("voice") if scenes and scenes[0].get("voice") else default_voice
    is_edge_voice = any(p in (first_voice or "") for p in ["bn-", "Neural", "en-US-", "en-GB-"])

    if engine_type in ["chatterbox", "chatterbox-bangla", "boson"]:
        log.info("Using Chatterbox-Bangla Voice Cloning Engine (BosonLab/chatterbox-bangla)")
        from src.narration.chatterbox_engine import ChatterboxBanglaEngine
        tts_engine = ChatterboxBanglaEngine(config)
    elif engine_type in ["clone", "f5", "f5-tts", "f5tts"]:
        log.info("Using F5-TTS Voice Cloning Engine (Zero-shot cloning from vocal audio)")
        from src.narration.f5_tts_engine import F5TTSCloningEngine
        tts_engine = F5TTSCloningEngine(config)
    elif engine_type in ["edge", "edge-tts"] or is_edge_voice:
        log.info("Using Edge-TTS Engine (High-quality Neural Voice / Bangla support)")
        from src.narration.edge_tts_engine import EdgeTTSEngine
        tts_engine = EdgeTTSEngine(config)
    else:
        log.info("Using Kokoro TTS Engine")
        from src.narration.kokoro_tts_engine import KokoroTTSEngine
        tts_engine = KokoroTTSEngine(config)

    # 4. Generate audio per sentence
    sentence_files = []
    log_banner("Generating Narration (Sentence-Level)")
    
    # Parse retry scenes if specified
    retry_scene_ids = set()
    if getattr(args, "retry_scenes", None):
        for part in args.retry_scenes.split(","):
            part = part.strip()
            if "-" in part:
                start_s, end_s = part.split("-", 1)
                retry_scene_ids.update(range(int(start_s), int(end_s) + 1))
            elif part.isdigit():
                retry_scene_ids.add(int(part))
        log.info(f"Targeting selective regeneration for scene(s): {sorted(list(retry_scene_ids))}")

    # Parse scene range if specified
    start_scene = getattr(args, "start_scene", 1) or 1
    end_scene = getattr(args, "end_scene", len(scenes)) or len(scenes)

    # 4. Generate audio per sentence / scene
    sentence_files = []
    log_banner("Generating Narration (Short Clip / Scene Caching Mode)")
    
    temp_dir = Path(config["paths"]["temp_dir"])
    temp_dir.mkdir(parents=True, exist_ok=True)

    for idx, scene in enumerate(scenes, start=1):
        if idx < start_scene or idx > end_scene:
            continue

        text = scene["text"]
        voice = scene["voice"]
        speed = scene["speed"]
        pause_after = scene["pause_after"]
        
        filename = f"clip_{idx:03d}.wav"
        out_file = temp_dir / filename
        force_retry = (idx in retry_scene_ids) or getattr(args, "force", False)

        log.info(f"\n--- Clip {idx}/{len(scenes)} ({len(text.split())} words) ---")
        log.info(f"  Text: \"{text[:70]}...\"")
        if voice:
            log.info(f"Voice override: {voice} | Speed override: {speed}")
            
        old_speed = tts_engine.speed
        if speed is not None:
            tts_engine.speed = speed

        if out_file.exists() and not force_retry:
            log.info(f"  [green]Cached[/green] -> {filename}")
            sentence_files.append({
                "path": out_file,
                "text": text,
                "pause_after": pause_after
            })
            tts_engine.speed = old_speed
            continue

        try:
            audio_path = tts_engine.generate_narration(text, filename, scene_id=None, voice=voice)
            sentence_files.append({
                "path": audio_path,
                "text": text,
                "pause_after": pause_after
            })
        except Exception as e:
            log.error(f"Failed to generate clip {idx}: {e}")
            sys.exit(1)

        tts_engine.speed = old_speed

    # 5. Concatenate sentences into final master file
    log_banner("Assembling Final Master Narration")
    if not sentence_files:
        log.error("No audio files were generated.")
        sys.exit(1)

    output_dir = Path(config["paths"]["output_audio"])
    output_dir.mkdir(parents=True, exist_ok=True)
    master_path = output_dir / f"{story_path.stem}.wav"

    log.info("Concatenating audio segments...")
    combined_audio = []
    sample_rate = None
    current_time = 0.0
    timestamp_lines = []

    for idx, item in enumerate(sentence_files, start=1):
        filepath = item["path"]
        pause_after = item["pause_after"]
        sent_text = item["text"]
        
        formatted_time = format_timestamp(current_time, fmt_type=ts_format)
        if ts_format == "bracket":
            timestamp_lines.append(f"{formatted_time} {sent_text}")
        else:
            timestamp_lines.append(f"{formatted_time} - {sent_text}")

        data, sr = sf.read(str(filepath))
        if sample_rate is None:
            sample_rate = sr
        elif sr != sample_rate:
            log.warning(f"Sample rate mismatch: {sr} != {sample_rate}. Using sample rate {sample_rate}.")
        
        combined_audio.append(data)
        
        segment_duration = len(data) / sr
        current_time += segment_duration
        
        if idx < len(sentence_files):
            silence_len = int(sr * pause_after)
            if len(data.shape) > 1:
                silence = np.zeros((silence_len, data.shape[1]), dtype=data.dtype)
            else:
                silence = np.zeros(silence_len, dtype=data.dtype)
            combined_audio.append(silence)
            current_time += pause_after

    if combined_audio:
        final_data = np.concatenate(combined_audio)

        # ── Export WAV ────────────────────────────────────────────────────
        sf.write(str(master_path), final_data, sample_rate)
        log.info(f"[bold green][OK] WAV saved:[/bold green] [cyan]{master_path}[/cyan]")

        # ── Export Timestamps ─────────────────────────────────────────────
        if ts_enabled:
            ts_path = master_path.parent / f"{story_path.stem}{ts_suffix}"
            try:
                with open(ts_path, "w", encoding="utf-8") as ts_file:
                    ts_file.write(f"# YouTube Timestamps for {story_path.name}\n")
                    ts_file.write(f"# Total Duration: {format_timestamp(current_time, ts_format)}\n\n")
                    for line in timestamp_lines:
                        ts_file.write(f"{line}\n")
                log.info(f"[bold green][OK] Timestamps saved:[/bold green] [cyan]{ts_path}[/cyan]")
                log.info("\n--- Generated Timestamps ---")
                for line in timestamp_lines:
                    log.info(f"  {line}")
                log.info("----------------------------\n")
            except Exception as e:
                log.warning(f"Failed to write timestamps file: {e}")

        # ── Export MP3 (320 kbps — highest quality) ───────────────────────
        mp3_path = master_path.with_suffix(".mp3")
        if HAS_PYDUB:
            try:
                audio_segment = AudioSegment.from_wav(str(master_path))
                audio_segment.export(
                    str(mp3_path),
                    format="mp3",
                    bitrate="320k",
                    parameters=["-q:a", "0"],
                )
                log.info(f"[bold green][OK] MP3 saved:[/bold green]  [cyan]{mp3_path}[/cyan]")
            except Exception as e:
                log.warning(f"MP3 export failed (ffmpeg missing?): {e}")
        else:
            log.info("MP3 export skipped (pydub/audioop not installed for this Python version). WAV is preserved at full lossless quality.")

        # ── Optional Cleanup of Temporary Scene Files ─────────────────────
        cleanup_cfg = config.get("cleanup", {})
        if cleanup_cfg.get("delete_temp_files", True):
            log.info("Cleaning up temporary audio segments...")
            for item in sentence_files:
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
    parser = argparse.ArgumentParser(description="AI Cinematic Story Narrator")
    parser.add_argument("--story", type=str, help="Path to story text or JSON file")
    parser.add_argument("--config", type=str, default="config/settings.yaml", help="Path to settings.yaml")
    parser.add_argument("--retry-scenes", type=str, help="Comma-separated or range list of scene numbers to regenerate (e.g. '4' or '4,7,12' or '3-6')")
    parser.add_argument("--start-scene", type=int, default=None, help="Generate starting from this scene number")
    parser.add_argument("--end-scene", type=int, default=None, help="Stop generating at this scene number")
    parser.add_argument("--force", action="store_true", help="Force regenerate all clips ignoring cache")
    args = parser.parse_args()
    
    run_pipeline(args)
