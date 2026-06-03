import os
import cv2
import numpy as np
from ppadb.client import Client as AdbClient
from datetime import datetime
import daily_reset

def main():
    # Check for Daily Reset (UTC 00:00)
    daily_reset.check_and_reset()

    # Load ADB Configuration
    ADB_ADDRESS = "192.168.2.11:5555"
    if os.path.exists("bot_settings.json"):
        import json
        try:
            with open("bot_settings.json", "r") as f:
                ADB_ADDRESS = json.load(f).get("adb_ip", ADB_ADDRESS)
        except: pass
    
    ADB_EXE = os.path.join("platform-tools", "adb.exe")
    
    # Try to start the ADB server if it's not running
    print("Checking ADB server...")
    os.system(f"{ADB_EXE} start-server")
    
    client = AdbClient(host="127.0.0.1", port=5037)
    
    try:
        device = client.device(ADB_ADDRESS)
    except Exception:
        device = None

    if not device:
        print(f"Attempting to connect to {ADB_ADDRESS}...")
        os.system(f"{ADB_EXE} connect {ADB_ADDRESS}")
        try:
            device = client.device(ADB_ADDRESS)
        except Exception:
            device = None
            
    if not device:
        print("\nFATAL ERROR: Could not connect to MuMu.")
        print(f"Please ensure MuMu is open and ADB is enabled in MuMu settings.")
        return

    # Ensure 'maps' directory exists
    if not os.path.exists("maps"):
        os.makedirs("maps")
        print("Created 'maps' directory.")

    # Capture the screen using ADB
    print(f"Capturing ADB screen from {ADB_ADDRESS}...")
    raw_screen = device.screencap()
    
    if not raw_screen:
        print("Error: Failed to capture screen via ADB.")
        return

    # Convert bytes to OpenCV image
    image_array = np.frombuffer(raw_screen, dtype=np.uint8)
    img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if img is None:
        print("Error: Could not decode ADB screenshot.")
        return

    # Save with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"maps/adb_map_{timestamp}.png"
    cv2.imwrite(filename, img)
    
    print(f"\nSUCCESS: Saved ADB map screenshot to {filename}")
    print(f"Dimensions: {img.shape[1]}x{img.shape[0]}")
    print("You can now run 'python .\\coordinate_mapper.py' to map this level.")

if __name__ == "__main__":
    main()
