import json
from pathlib import Path

def analyze():
    stories_dir = Path("input/stories")
    txt_files = sorted(list(stories_dir.glob("story part *.txt")), key=lambda p: int(p.stem.split("part ")[1]))
    
    print(f"{'Story Part':<15} | {'Orig Words':<10} | {'Opt Words':<10} | {'Diff':<10} | {'% Retained':<12}")
    print("-" * 65)
    
    for txt_path in txt_files:
        json_path = txt_path.with_suffix(".json")
        if not json_path.exists():
            continue
            
        with open(txt_path, "r", encoding="utf-8") as f:
            txt_content = f.read()
            
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            
        # Extract narration texts
        scenes = json_data.get("scenes", [])
        opt_texts = [s.get("text", "") for s in scenes]
        opt_content = " ".join(opt_texts)
        
        # Word counts
        orig_words = len(txt_content.split())
        opt_words = len(opt_content.split())
        diff = opt_words - orig_words
        retained = (opt_words / orig_words) * 100 if orig_words > 0 else 0
        
        print(f"{txt_path.stem:<15} | {orig_words:<10} | {opt_words:<10} | {diff:<10} | {retained:.1f}%")
        
        # Print first/last 60 characters to see semantic matching
        print(f"  -> Orig Start: {txt_content[:70].strip()}...")
        print(f"  -> Opt  Start: {opt_texts[0][:70].strip()}...")
        print(f"  -> Orig End  : {txt_content[-70:].strip()}...")
        print(f"  -> Opt  End  : {opt_texts[-1][:70].strip()}...")
        print("-" * 65)

if __name__ == "__main__":
    analyze()
