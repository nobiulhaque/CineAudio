# 🎙️ AI Cinematic Story Narrator

A professional-grade AI narration pipeline powered by **Qwen3-TTS** — designed to generate deep, cinematic, emotionally-charged voice-overs for epic storytelling.

---

## 🚀 Quick Start — How to Run

### Step 1 — Activate the virtual environment
Open a terminal in the project folder and run:
```powershell
.venv\Scripts\activate
```

### Step 2 — Run the narrator
```powershell
python main.py --story input/stories/example_horror.txt
```

That's it. The narration will be saved to `output/audio/final_narration.wav`.

---

## 📁 Project Structure

```
CineAudio/
├── main.py                         ← Entry point (run this!)
├── config/
│   └── settings.yaml               ← Voice design & settings
├── input/
│   └── stories/
│       └── example_horror.txt      ← Your story goes here
├── output/
│   └── audio/                      ← Generated narration output
│       ├── scene_001.wav
│       ├── scene_002.wav
│       └── final_narration.wav     ← Final combined narration
└── src/
    ├── narration/
    │   └── qwen_tts_engine.py      ← Qwen3-TTS narration engine
    └── utils/
        ├── config_loader.py
        └── logger.py
```

---

## 🎭 Voice Design

The voice character is configured in [`config/settings.yaml`](config/settings.yaml):

```yaml
voice_design:
  gender: "Male"
  age: "Middle-aged"
  pitch: "deep baritone"
  pace: "deliberate with dramatic pauses"
  emotion: "intense and serious"
  characteristics: "magnetic, gravelly, rich, resonant"
```

This generates an instruction like:
> *"Speak in a deep baritone voice, male, middle-aged, speaking deliberate with dramatic pauses, with an intense and serious tone, sounding magnetic, gravelly, rich, resonant."*

**To change the voice character**, edit the `voice_design` block in `settings.yaml`. The model understands natural language descriptions — be expressive!

---

## 📝 Adding Your Own Story

1. Create a `.txt` file in `input/stories/`
2. Write your story — **separate paragraphs with a blank line** (double newline)
3. Run: `python main.py --story input/stories/your_story.txt`

Each paragraph is narrated separately and then joined with a dramatic 0.8-second pause.

**Example format:**
```
In the beginning, there was only darkness. The world held its breath, 
waiting for the storm that was coming.

A single flame flickered at the edge of the abyss. Ancient and eternal,
it burned with the fury of a thousand suns.

And then — silence. The kind of silence that comes before catastrophe.
```

---

## ⚙️ System Requirements

| Component | Requirement |
|-----------|-------------|
| GPU | NVIDIA (CUDA 12.1) — RTX 2060 12GB+ recommended |
| Python | 3.12 |
| SoX | System tool (installed via winget) |
| Model | Auto-downloaded from HuggingFace on first run |

---

## 🛠️ Troubleshooting

### "SoX not found" warning
This is a warning from torchaudio — it does **not** stop the narration from working. SoX handles optional audio resampling. Install it with:
```powershell
winget install --id=ChrisBagwell.SoX -e
```
Then restart your terminal.

### Red underlines in VS Code (`soundfile`, `qwen_tts`)
This means VS Code is using the wrong Python. A `.vscode/settings.json` has been created to fix this automatically. Press **Ctrl+Shift+P** → "Python: Select Interpreter" → choose `.venv\Scripts\python.exe`.

### "Module compiled with NumPy 1.x" error
```powershell
.venv\Scripts\pip install "numpy<2"
```

### First run is slow
The Qwen3-TTS model (~3-7 GB) is downloaded from HuggingFace on the first run. Subsequent runs start instantly from cache.
