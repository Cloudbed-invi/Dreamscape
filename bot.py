import time
import cv2
import sys
import numpy as np
import easyocr
import mss
from ppadb.client import Client as AdbClient
from thefuzz import process

# ==========================================
# CONFIGURATIONS
# ==========================================
DRY_RUN = False

import json
import os

# Try to load the automatically generated region configuration from region_selector.py
region_config_path = "region.json"
if not os.path.exists(region_config_path):
    print(f"CRITICAL ERROR: '{region_config_path}' not found!")
    print("Please run 'python .\\region_selector.py' first to draw your capture box.")
    sys.exit(1)

with open(region_config_path, 'r') as f:
    CAPTURE_REGION = json.load(f)

print(f"Loaded CAPTURE_REGION from config: {CAPTURE_REGION}")

# Paste your 30 mapped coordinates here
master_dict = {
    'pouch': (736, 620),
    'steak': (800, 572),
    'harpoon': (720, 494),
    'cat': (480, 686),
    'sea turtle': (184, 650),
    'hot air balloon': (472, 152),
    'window': (652, 246),
    'fishing net': (610, 730),
    'potato': (248, 842),
    'oar': (670, 668),
    'oxygen tank': (380, 718),
    'fishing rod': (350, 602),
    'z': (584, 252),
    'whale': (196, 564),
    'rudder': (272, 502),
    'seahorse': (672, 534),
    'signboard': (670, 398),
    'lighthouse': (222, 286),
    'sailboat': (110, 382),
    'volleyball': (256, 710),
    'exhaust fan': (780, 262),
    'pumpkin': (120, 814),
    'parasol': (444, 476),
    'backpack': (572, 564),
    'lifebuoy': (382, 654),
    'chimney': (124, 456),
    'drifting bottle': (172, 754),
    'jar': (800, 684),
    'bench': (390, 558),
    'flag': (196, 442),
    'crane': (530, 388),
    'submarine': (336, 412),
    'seagull': (400, 282),
    'patch': (796, 486),
    'plane': (144, 170),
}

def main():
    print("Initializing ADB Client...")
    client = AdbClient(host="127.0.0.1", port=5037)
    
    try:
        device = client.device("127.0.0.1:5555")
    except RuntimeError as e:
        print(f"Error communicating with ADB server: {e}")
        sys.exit(1)
        
    if not device:
        print("Exit: Device 127.0.0.1:5555 not found. Please ensure it is connected.")
        sys.exit(1)
        
    print("Device connected successfully!")

    print("Initializing EasyOCR reader. This may take a moment...")
    reader = easyocr.Reader(['en'], gpu=True)
    print("EasyOCR initialized.")
    
    # Init mss for zero-latency screen capture
    sct = mss.mss()

    print(f"Starting High-Speed Main Loop... DRY_RUN is set to {DRY_RUN}")
    print("Press Ctrl+C to exit.\n")
    
    # Keep track of recent taps to avoid double-clicking items before they animate away
    recent_taps = {}
    COOLDOWN_TIME = 1.5  # Seconds an item is ignored after being tapped
    
    # The High-Speed Main Loop (while True)
    while True:
        try:
            # Clean up expired cooldowns
            current_time = time.time()
            recent_taps = {k: v for k, v in recent_taps.items() if current_time - v < COOLDOWN_TIME}
            
            # 1. Instant Vision: Grab the CAPTURE_REGION using mss
            # Ensure the [USER_FILL_IN] values are replaced with actual integers before running
            sct_img = sct.grab(CAPTURE_REGION)
            
            # Convert mss screen grab to NumPy array
            # sct_img is BGRA, cv2.cvtColor can handle it
            img = np.array(sct_img)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            
            # Apply cv2.threshold
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            
            # 2. Batch Read: Pass to reader.readtext(detail=0)
            detected_strings = reader.readtext(thresh, detail=0)
            
            if not detected_strings:
                continue
                
            # 3. Batch Process
            taps_to_make = []
            
            # Loop through all detected text strings
            for string in detected_strings:
                clean_string = string.lower().strip()
                if not clean_string or not master_dict:
                    continue
                    
                match_result = process.extractOne(clean_string, master_dict.keys())
                if match_result:
                    match, score = match_result
                    
                    if score >= 85:
                        # Prevent DOUBLE CLICKING the exact same item within the cooldown window
                        if match in recent_taps:
                            continue
                            
                        x, y = master_dict[match]
                        # Avoid duplicate targets in a single batch
                        if not any(m == match for m, _, _ in taps_to_make):
                            taps_to_make.append((match, x, y))
                            
            # 4. The Strike
            if taps_to_make:
                # Limit to 2 taps per screenshot batch
                targets = taps_to_make[:2]
                
                if DRY_RUN:
                    print(f"[DRY RUN] Saw {len(targets)} targets: " + " | ".join(f"'{m}' at ({x}, {y})" for m, x, y in targets))
                else:
                    detected_names = []
                    for name, x, y in targets:
                        # Add to the memory bank FIRST so we don't hit it again next cycle
                        recent_taps[name] = time.time()
                        
                        # Non-blocking sequential tap execution
                        device.shell(f"input tap {x} {y}")
                        detected_names.append(name)
                        
                        # Add a tiny stagger gap between the taps
                        time.sleep(0.23)
                    
                    print(f"[STRIKE] Fired staggered taps: {detected_names}")
                    
                # Base sleep to let the game drop the next items into the queue
                time.sleep(0.32)

        except KeyboardInterrupt:
            print("\nBot strictly stopped by user.")
            break
        except Exception as e:
            print(f"An error occurred in the loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
