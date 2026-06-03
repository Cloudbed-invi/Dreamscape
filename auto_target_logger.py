import os
import time
import cv2
import numpy as np
import easyocr
import mss
import json
import daily_reset

def is_valid_word(word):
    """Strict check to ensure word is a likely game item."""
    w = word.strip()
    # 1. Must be 3-15 chars
    if not (3 <= len(w) <= 15): return False
    # 2. Must be mostly alphabetic
    if not w.replace(" ", "").isalpha(): return False
    # 3. Vowel check (prevents jumbled consonants like 'shrtxp')
    vowels = set("aeiouAEIOU")
    if not any(char in vowels for char in w): return False
    return True

def main():
    # Check for Daily Reset (UTC 00:00)
    daily_reset.check_and_reset()

    # Load calibrated OCR region
    region_config_path = "region.json"
    if not os.path.exists(region_config_path):
        print(f"Error: Calibration needed.")
        return

    with open(region_config_path, 'r') as f:
        config = json.load(f)
    ocr_region = config['ocr_list']

    reader = easyocr.Reader(['en'], gpu=True)
    sct = mss.mss()

    # Load existing targets
    known_targets = set()
    if os.path.exists("targets.txt"):
        with open("targets.txt", "r") as f:
            known_targets = {line.strip().lower() for line in f if line.strip()}

    print(f"--- Wordlist Logger Active ---")
    
    blacklist = ["success", "saved", "dimensions", "mapper", "coordinate", "initialized", "starting", "teacher", "found", "target"]

    try:
        while True:
            sct_img = sct.grab(ocr_region)
            img = np.array(sct_img)
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            
            detected_strings = reader.readtext(thresh, detail=0)
            
            for string in detected_strings:
                clean = string.strip()
                lower_clean = clean.lower()
                
                # Apply the new Smart Filter
                if not is_valid_word(clean): continue
                if any(word in lower_clean for word in blacklist): continue
                
                if lower_clean not in known_targets:
                    print(f"✨ New Target: {clean}")
                    known_targets.add(lower_clean)
                    with open("targets.txt", "a") as f:
                        f.write(f"{clean}\n")
            
            time.sleep(0.8) # Constant monitoring

    except (KeyboardInterrupt, SystemExit):
        print("\nLogger stopped.")

if __name__ == "__main__":
    main()
