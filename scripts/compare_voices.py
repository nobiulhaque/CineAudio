"""
Compare available Kokoro American Male voices to choose the best one.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils.config_loader import load_config
from src.narration.kokoro_tts_engine import KokoroTTSEngine

def main():
    print("Loading configuration...")
    config = load_config("config/settings.yaml")
    
    print("Initializing KokoroTTSEngine...")
    try:
        engine = KokoroTTSEngine(config)
    except Exception as e:
        print(f"[ERROR] Failed to initialize engine: {e}")
        sys.exit(1)

    test_text = "He stood in the dark, close to the microphone. The whispers were coming from inside the walls."
    
    voices = ["am_adam", "am_echo", "am_eric", "am_fenrir", "am_michael"]
    
    print("\nGenerating comparison samples...")
    for voice in voices:
        output_file = f"compare_{voice}.wav"
        print(f"\n--- Testing voice: {voice} ---")
        try:
            out_path = engine.generate_narration(test_text, output_file, voice=voice)
            print(f"[SUCCESS] Saved: {out_path.name}")
        except Exception as e:
            print(f"[ERROR] Failed to generate for {voice}: {e}")

if __name__ == "__main__":
    main()
