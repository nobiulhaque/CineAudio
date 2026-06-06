"""
Simple test script to verify that Kokoro TTS and KPipeline are working correctly.
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
        print(f"\n[ERROR] Failed to initialize engine: {e}")
        print("\nMake sure eSpeak NG is installed on your system.")
        print("You can install it with: winget install -e --id eSpeak-NG.eSpeak-NG")
        sys.exit(1)

    test_text = "Hello! This is a test of the new Kokoro text to speech engine. It works beautifully."
    output_file = "test_kokoro.wav"
    
    print(f"Generating test audio for: \"{test_text}\"")
    try:
        out_path = engine.generate_narration(test_text, output_file)
        print(f"\n[SUCCESS] Audio generated successfully!")
        print(f"Output saved to: {out_path.resolve()}")
    except Exception as e:
        print(f"\n[ERROR] Generation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
