import time
import os
import cv2
import numpy as np
import easyocr
import mss
import json
import capture_map
import auto_target_logger
import daily_reset

def main():
    # 0. Check for Daily Reset
    daily_reset.check_and_reset()

    # Load calibrated OCR region
    region_config_path = "region.json"
    if not os.path.exists(region_config_path):
        print(f"Error: '{region_config_path}' not found! Run region_selector.py first.")
        return

    with open(region_config_path, 'r') as f:
        config = json.load(f)
    ocr_region = config['ocr_list']

    print("Initializing Auto-Setup System...")
    reader = easyocr.Reader(['en'], gpu=True)
    sct = mss.mss()

    print(f"\n--- STANDBY MODE ---")
    print("I am waiting for the countdown to end and the level to start...")
    print("Once I detect the item list at the bottom, I will capture the map and start logging.")
    
    level_started = False
    try:
        while not level_started:
            # 1. Capture OCR area to check for game start
            sct_img = sct.grab(ocr_region)
            img = np.array(sct_img)
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            
            # 2. Check if multiple real words exist (Game Started)
            detected = reader.readtext(thresh, detail=0)
            
            # Stricter Filter: Must be > 2 chars and only alphabets/spaces (no symbols)
            valid_text = [t for t in detected if len(t.strip()) > 2 and t.strip().replace(" ", "").isalpha()]
            
            if len(valid_text) >= 2: # Wait for at least 2 clear words
                print(f"\n🚀 GAME DETECTED! (Items found: {valid_text})")
                level_started = True
            else:
                time.sleep(0.5)

        # 3. Trigger Map Capture
        print("📸 Capturing map screenshot immediately...")
        capture_map.main()

        # 4. Trigger Teacher Mode
        print("📝 Starting Target Logger...")
        auto_target_logger.main()

    except KeyboardInterrupt:
        print("\nAuto-Setup cancelled.")

if __name__ == "__main__":
    main()
