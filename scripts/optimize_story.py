"""
LLM Story Optimizer
Converts a raw story text file into an optimized structured JSON file for narration.
"""

import os
import sys
import json
import argparse
from pathlib import Path
import requests

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils.config_loader import load_config
from src.utils.logger import get_logger, log_banner

log = get_logger("optimizer")

def optimize_story(story_path: Path, config: dict, output_path: Path) -> None:
    llm_cfg = config.get("llm", {})
    api_key = llm_cfg.get("api_key") or os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        log.error(
            "API key not found. Please add your key to 'config/settings.yaml' (under llm.api_key) "
            "or set one of the environment variables: GROQ_API_KEY, XAI_API_KEY, OPENAI_API_KEY."
        )
        sys.exit(1)
        
    base_url = llm_cfg.get("base_url", "https://api.groq.com/openai/v1")
    model = llm_cfg.get("model", "llama-3.3-70b-versatile")
    
    log.info(f"Reading story text: {story_path}")
    with open(story_path, "r", encoding="utf-8") as f:
        story_text = f.read()

    log.info("Preparing LLM prompt...")
    
    system_prompt = (
        "You are an expert audio narration and cinematic storytelling producer.\n"
        "Your task is to take a raw story text, optimize it for a full-length, deep, immersive cinematic YouTube video narration, and output it as a structured JSON configuration.\n\n"
        "RULES FOR THE PROCESSING:\n"
        "1. Do NOT summarize, shorten, simplify, truncate, rewrite, or cut ANY information, sentences, details, descriptors, lists, or vocabulary from the original text. You must retain 100% of the original story, details, and literary style (specifically maintaining Lovecraft's atmospheric and descriptive adjectives/structure).\n"
        "2. Keep the author's original words intact. Do not alter vocabulary, grammar, or sentence structure.\n"
        "3. Segment the text into natural paragraphs/scenes suitable for narration, preserving the exact original sentences/words within each segment.\n"
        "4. Enforce vocal consistency: Use ONE single voice profile consistently across the entire story (e.g., 'am_michael'). Do NOT change voices between scenes/segments.\n"
        "5. Do not discard or skip any title introductions, credits, copyright disclaimers, or introductory text if present. Keep them word-for-word.\n\n"
        "Available voice profiles (all high quality Kokoro TTS voices):\n"
        "- 'am_michael': Standard narration voice, smooth, warm, podcast style. (Recommended default narrator)\n"
        "- 'am_fenrir': Crisp, dry, whispery close-mic voice. Great for creepy whispers, thoughts, mystery, secrets, or quiet horror scenes.\n"
        "- 'am_adam': Deep, resonant male voice. Great for authoritative, epic, or very heavy, intense narration segments.\n"
        "- 'am_echo': Clear and direct voice.\n"
        "- 'am_eric': Deep male voice.\n\n"
        "For each section, determine:\n"
        "1. scene_title: A very short, engaging, descriptive title for this specific segment (e.g., 'The Secret Room' or 'The Whisper in the Dark') to be used for YouTube timestamps. Do not use generic names like 'Scene 1'.\n"
        "2. The original text of that section (must be word-for-word identical to the source text, no paraphrasing/rewriting).\n"
        "3. The voice (must be identical to the voice used in all other scenes to maintain uniform narration).\n"
        "4. Speed: pace of reading. Default is 0.9. Slower (e.g. 0.85) for suspenseful/tense parts, faster (e.g. 0.95 or 1.0) for action or urgency.\n"
        "5. pause_after: The pause duration in seconds to add AFTER this segment before starting the next one. Default is 0.8. Use longer pauses (e.g., 1.2 to 2.5 seconds) after suspenseful cliffhangers, sudden stops, or scene transitions.\n\n"
        "You must output ONLY valid JSON matching this schema, without any markdown code blocks or explanations:\n"
        "{\n"
        "  \"title\": \"Title of the Story\",\n"
        "  \"scenes\": [\n"
        "    {\n"
        "      \"scene_title\": \"short section title\",\n"
        "      \"text\": \"original narration text\",\n"
        "      \"voice\": \"am_michael\",\n"
        "      \"speed\": 0.9,\n"
        "      \"pause_after\": 1.2\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    user_prompt = f"Convert this story into the structured narration JSON format, retaining 100% of the original text word-for-word:\n\n{story_text}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    log.info(f"Connecting to LLM API ({base_url}) using model {model}...")
    try:
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result_json = response.json()
        
        content = result_json["choices"][0]["message"]["content"].strip()
        
        # Parse content to make sure it is valid JSON
        parsed_story = json.loads(content)
        
        # Save output JSON
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(parsed_story, f, indent=2, ensure_ascii=False)
            
        log.info(f"[SUCCESS] Story optimized and saved to: {output_path}")
        
    except Exception as e:
        log.error(f"Failed to communicate with LLM API or parse response: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            log.debug(f"API Response Text: {response.text}")
        sys.exit(1)

def main():
    log_banner("AI Cinematic Story Optimizer")
    
    parser = argparse.ArgumentParser(description="Optimize a raw story for cinematic narration.")
    parser.add_argument("--story", type=str, help="Path to story text file")
    parser.add_argument("--config", type=str, default="config/settings.yaml", help="Path to settings.yaml")
    parser.add_argument("--output", type=str, help="Path to output JSON file (optional)")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    if args.story:
        story_path = Path(args.story)
    else:
        story_path = Path(config["paths"]["input_stories"]) / "example_horror.txt"
        
    if not story_path.exists():
        log.error(f"Story file not found: {story_path}")
        sys.exit(1)
        
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = story_path.with_suffix(".json")
        
    optimize_story(story_path, config, output_path)

if __name__ == "__main__":
    main()
