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
        "Your task is to take a raw story text and convert it into a structured JSON configuration "
        "optimized for text-to-speech narration. You must break the story into paragraphs/scenes "
        "and suggest narration variables for each section.\n\n"
        "Available voice profiles (all high quality Kokoro TTS voices):\n"
        "- 'am_michael': Standard narration voice, smooth, warm, podcast style. (Use this as default)\n"
        "- 'am_fenrir': Crisp, dry, whispery close-mic voice. Great for creepy whispers, thoughts, or quiet horror scenes.\n"
        "- 'am_adam': Deep, resonant male voice. Great for authoritative or very heavy, intense narration segments.\n"
        "- 'am_echo': Clear and direct voice.\n"
        "- 'am_eric': Deep male voice.\n\n"
        "For each section, determine:\n"
        "1. The narrative text to read (slightly clean up if there are any typographical formatting issues, but do not change the words unless it enhances readability/phonetic delivery).\n"
        "2. The optimal voice (use am_michael by default, switch to am_fenrir for creepy or whispering segments, or am_adam for very deep segments).\n"
        "3. Speed: pace of reading. Default is 0.9. Slower (e.g. 0.85) for suspenseful/tense parts, faster (e.g. 0.95 or 1.0) for action or urgency.\n"
        "4. pause_after: The pause duration in seconds to add AFTER this segment before starting the next one. Default is 0.8. Use longer pauses (e.g., 1.5 to 2.5 seconds) after suspenseful cliffhangers, sudden stops, or scene transitions.\n\n"
        "You must output ONLY valid JSON matching this schema, without any markdown code blocks or explanations:\n"
        "{\n"
        "  \"title\": \"Title of the Story\",\n"
        "  \"scenes\": [\n"
        "    {\n"
        "      \"text\": \"narration text\",\n"
        "      \"voice\": \"am_michael\",\n"
        "      \"speed\": 0.9,\n"
        "      \"pause_after\": 1.2\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    user_prompt = f"Convert this story into the optimized narration JSON format:\n\n{story_text}"

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
