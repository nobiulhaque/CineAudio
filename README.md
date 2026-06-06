# 🎙️ AI Cinematic Story Narrator (Kokoro Edition)

A professional-grade, high-performance AI narration pipeline powered by **Kokoro-82M TTS** and **Groq LLM** — designed to generate deep, cinematic, emotionally-charged, and dynamically paced voice-overs for epic storytelling.

---

## ✨ Features

- **Blazing Fast Narration**: Generates hours of high-quality narration in seconds using Kokoro TTS on CUDA.
- **Dynamic Voice & Pacing Control**: Supports switching voices (e.g., standard narrator to quiet whispering characters), adjusting reading speeds, and configuring custom pauses per paragraph using a structured JSON script.
- **LLM Story Optimizer**: Automatically converts raw stories into optimized narration JSON files using Groq (Llama 3.3) or xAI Grok.
- **Automatic Cleanup**: Automatically deletes temporary segment files after compiling the final master audio tracks.
- **WAV & High-Bitrate MP3 Exports**: Generates both lossless 24kHz WAV and premium 320kbps MP3 final tracks.

---

## 🚀 Quick Start — How to Run

### Step 1 — Install System Dependencies
On Windows, Kokoro TTS requires **eSpeak NG** for grapheme-to-phoneme (text-to-sound) conversion.
Open **PowerShell (as Administrator)** and run:
```powershell
winget install -e --id eSpeak-NG.eSpeak-NG
```
*(Note: Please restart your terminal/IDE after installing so that the environment variables take effect. The engine will locate the installation path automatically).*

### Step 2 — Activate the Virtual Environment
Open a terminal in the project folder and run:
```powershell
.venv\Scripts\activate
```

### Step 3 — Add Your LLM API Key (Optional)
To use the automatic story optimizer, edit `config/settings.yaml` and paste your Groq or xAI API key:
```yaml
llm:
  api_key: "your_groq_or_grok_key_here"
```

### Step 4 — Run the Pipeline

1. **Optimize a story** (converts a text story to a structured narration JSON):
   ```bash
   python scripts/optimize_story.py --story input/stories/example_horror.txt
   ```
2. **Generate the narration**:
   ```bash
   python main.py --story input/stories/example_horror.json
   ```

Your final master audio file will be saved in `output/audio/final_narration.mp3` and `final_narration.wav`.

---

## 📁 Project Structure

```
CineAudio/
├── main.py                         ← Main pipeline entry point
├── config/
│   └── settings.yaml               ← Master config (API keys, default voice settings)
├── input/
│   └── stories/
│       ├── example_horror.txt      ← Raw story files
│       └── example_horror.json     ← Optimized JSON configuration
├── output/
│   └── audio/                      ← Final audio outputs (.wav, .mp3)
├── scripts/
│   ├── optimize_story.py           ← LLM text-to-JSON optimizer
│   └── compare_voices.py           ← Script to hear different Kokoro voices
└── src/
    ├── narration/
    │   └── kokoro_tts_engine.py    ← Kokoro KPipeline wrapper
    └── utils/
        ├── config_loader.py
        └── logger.py
```

---

## 🎭 Narration Customization (JSON)

When running the pipeline using a `.json` story file, you can customize the voice, speed, and pause after each paragraph:

```json
{
  "title": "My Cinematic Story",
  "scenes": [
    {
      "text": "The wind didn’t just howl that night—it spoke.",
      "voice": "am_michael",
      "speed": 0.9,
      "pause_after": 1.5
    },
    {
      "text": "Don’t stay too long.",
      "voice": "am_fenrir",
      "speed": 0.8,
      "pause_after": 2.5
    }
  ]
}
```

### Voice Options (American Male):
- `am_michael`: Smooth, warm podcast style voice (Default narrator).
- `am_fenrir`: Crisp, dry, whispery close-mic voice (Great for creepy voices).
- `am_adam`: Deep, heavy, resonant narration voice.
- `am_echo` / `am_eric`: Alternative deep voices.

---

## ⚙️ System Requirements

| Component | Requirement |
|-----------|-------------|
| GPU | NVIDIA (CUDA 12.1) — RTX 2060 12GB+ recommended |
| OS | Windows (eSpeak NG installed via winget) |
| Python | 3.12 |
| Model | Kokoro-82M (Auto-downloaded on first run) |
