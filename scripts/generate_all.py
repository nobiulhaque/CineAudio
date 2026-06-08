import os
import sys
import subprocess
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils.logger import get_logger, log_banner

log = get_logger("generate_all")

def main():
    log_banner("Batch Story Optimizer & Narrator")
    
    python_exe = sys.executable
    stories_dir = Path("input/stories")
    story_files = sorted(list(stories_dir.glob("story part *.txt")), key=lambda p: int(p.stem.split("part ")[1]))
    
    if not story_files:
        log.error("No 'story part *.txt' files found in input/stories.")
        sys.exit(1)
        
    log.info(f"Found {len(story_files)} story part(s) to process.")
    
    for story_path in story_files:
        part_name = story_path.stem
        log_banner(f"Processing: {part_name}")
        
        json_path = story_path.with_suffix(".json")
        
        # 1. Run LLM Story Optimizer if JSON doesn't exist
        if not json_path.exists():
            log.info(f"Optimizing story text to JSON: {story_path} -> {json_path}")
            opt_cmd = [python_exe, "scripts/optimize_story.py", "--story", str(story_path)]
            try:
                subprocess.run(opt_cmd, check=True)
            except subprocess.CalledProcessError as e:
                log.error(f"Failed to optimize {part_name}: {e}")
                continue
        else:
            log.info(f"JSON already exists, skipping optimization: {json_path}")
            
        # 2. Run Main Pipeline to generate audio
        log.info(f"Generating audio narration for: {json_path}")
        gen_cmd = [python_exe, "main.py", "--story", str(json_path)]
        try:
            subprocess.run(gen_cmd, check=True)
            log.info(f"[SUCCESS] Completed generation for {part_name}!")
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to generate audio for {part_name}: {e}")

if __name__ == "__main__":
    main()
