import time
import cv2
import sys
import numpy as np
import easyocr
from ppadb.client import Client as AdbClient
from thefuzz import process

# ==========================================
# CONFIGURATIONS
# ==========================================
# DRY_RUN Toggle
# If True, it only prints the target we intend to tap (useful for testing).
# If False, it actually executes the ADB tap.
DRY_RUN = False

# Paste your generated coordinate dictionary here
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
}


def main():
    print("Initializing ADB Client...")
    # Initialize the ADB client (127.0.0.1, port 5037)
    client = AdbClient(host="127.0.0.1", port=5037)
    
    # Connect to device 127.0.0.1:5555
    # ppadb connect returns boolean if connection was successful or not, but we can just use .device()
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
    # Initialize the EasyOCR reader
    reader = easyocr.Reader(['en'], gpu=True)
    print("EasyOCR initialized.")

    print(f"Starting Main Loop... DRY_RUN is set to {DRY_RUN}")
    print("Press Ctrl+C to exit.\n")
    
    # The Main Loop (while True)
    while True:
        try:
            # 1. Vision: Use device.screencap() to grab the screen
            screenshot = device.screencap()
            if screenshot is None:
                continue
            
            # Decode it with NumPy/OpenCV
            img_array = np.frombuffer(screenshot, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is None:
                continue
                
            # Crop the image strictly to the bottom UI: img[1200:1600, 0:900]
            cropped = img[1200:1600, 0:900]
            
            # 2. OCR Preprocessing: Convert the cropped image to grayscale
            gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
            
            # Apply a binary threshold (cv2.threshold) to make the text stark black-and-white
            # Using 200 as the threshold cut-off, creating maximum contrast
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            
            # 3. Reading: Pass the processed image to reader.readtext(detail=0)
            detected_strings = reader.readtext(thresh, detail=0)
            
            if not detected_strings:
                continue

            # 4. Match and Strike Logic
            # Iterate through the detected strings
            for string in detected_strings:
                # Lowercase them
                clean_string = string.lower().strip()
                
                if not clean_string:
                    continue
                    
                # Use process.extractOne to check the string against the keys in master_dict
                if not master_dict:
                    break # Skip matching if dictionary is empty
                    
                match_result = process.extractOne(clean_string, master_dict.keys())
                
                if match_result:
                    match, score = match_result
                    
                    # If a match is found with a score of >= 85
                    if score >= 85:
                        # Get the (X, Y) from the dictionary
                        x, y = master_dict[match]
                        
                        if DRY_RUN:
                            print(f"[DRY RUN] Saw '{string}'. Best match is '{match}'. Would tap ({x}, {y}).")
                        else:
                            # Execute the tap
                            device.shell(f"input tap {x} {y}")
                            print(f"[STRIKE] Tapped '{match}' at ({x}, {y}).")
                            
                        # CRITICAL: Instantly break out of the string-iteration loop. 
                        # We only want ONE tap per screenshot.
                        time.sleep(0.5)
                        break

        except KeyboardInterrupt:
            print("\nBot strictly stopped by user.")
            break
        except Exception as e:
            print(f"An error occurred in the loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
