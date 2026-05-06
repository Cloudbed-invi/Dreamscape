import time
import random
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
    'Crow': (306, 126),
    'Trumpet': (432, 394),
    'Cake': (388, 1222),
    'Glass Jar': (500, 832),
    'Chimney': (404, 144),
    'Sun': (568, 768),
    'Moon': (704, 874),
    'Star': (140, 206),
    'Scarf': (790, 952),
    'Suitcase': (210, 742),
    'Hot-Air-Balloon': (614, 402),
    'Hole': (488, 294),
    'Fork': (646, 1084),
    'Key': (144, 1062),
    'Fountain Pen': (226, 1014),
    'Goggles': (202, 1258),
    'Giftbox': (350, 814),
    'Fish Bone': (608, 1232),
    'Rose': (714, 448),
    'Accordion': (784, 1276),
    'Flour': (406, 750),
    'Music Note': (390, 944),
    'Corn': (496, 760),
    'Car': (236, 900),
    'Yarn Ball': (816, 1116),
    'Lollipop': (728, 746),
    'Bread Slice': (312, 1102),
    'Umbrella': (296, 750),
    'Satchel': (710, 1020),
    'Diary': (96, 1182),
    'Paw Mark': (112, 968),
    'Ring': (578, 1146),
    'Pocket Watch': (382, 1038),
    'Coffee Cup': (544, 1060),
    'Envelope': (188, 954),
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
                        
                        # Humanize the exact tap coordinates slightly to avoid bot detection
                        rand_x = x + random.randint(-8, 8)
                        rand_y = y + random.randint(-8, 8)
                        
                        # Non-blocking sequential tap execution
                        device.shell(f"input tap {rand_x} {rand_y}")
                        detected_names.append(name)
                        
                        # Add a random stagger gap between the taps to simulate human speed variations
                        time.sleep(random.uniform(0.05, 0.35)) #(0.55, 0.85)
                    
                    print(f"[STRIKE] Fired staggered taps: {detected_names}")
                    
                # Base sleep with a human-like random delay before processing the next batch
                time.sleep(random.uniform(0.15, 0.35)) #(0.65, 0.95)

        except KeyboardInterrupt:
            print("\nBot strictly stopped by user.")
            break
        except Exception as e:
            print(f"An error occurred in the loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
