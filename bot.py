import time
import random
import cv2
import sys
import numpy as np
import easyocr
import mss
from ppadb.client import Client as AdbClient
from thefuzz import process
import json
import os
import ast
import tkinter as tk

# --- PRODUCT CONFIGURATION ---
DRY_RUN = False
# --- DYNAMIC SETTINGS ---
def load_settings():
    defaults = {
        "adb_ip": "192.168.2.11:5555",
        "reaction": 0.1, 
        "cooldown": 0.1, 
        "jitter": 4, 
        "randomness": 0.2
    }
    if os.path.exists("bot_settings.json"):
        try:
            with open("bot_settings.json", "r") as f: return json.load(f)
        except: pass
    return defaults

settings = load_settings()
ADB_ADDRESS = settings.get("adb_ip", "192.168.2.11:5555")
base_react = settings["reaction"]
base_cool = settings["cooldown"]
var = settings["randomness"]
HUMAN_REACTION_RANGE = (max(0, base_react * (1 - var)), base_react * (1 + var))
SUCCESS_COOLDOWN = (max(0, base_cool * (1 - var)), base_cool * (1 + var))
HUMAN_CLICK_OFFSET = settings["jitter"]

class StrikeOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.7)
        self.root.geometry("300x35+350+10")
        self.label = tk.Label(self.root, text="Bot Active", bg="#121212", fg="#00ff00", font=("Arial", 10, "bold"))
        self.label.pack(fill="both", expand=True)
        self.root.update()

    def update(self, text):
        self.label.config(text=text)
        self.root.update()

def main():
    with open("region.json", 'r') as f:
        config = json.load(f)
    capture_region = config['ocr_list']

    with open("master_dict.txt", "r") as f:
        content = f.read().replace("master_dict = ", "").strip()
        master_dict = ast.literal_eval(content)

    client = AdbClient(host="127.0.0.1", port=5037)
    device = client.device(ADB_ADDRESS)
    
    # SPEED OPTIMIZATION: Only look for letters and spaces
    reader = easyocr.Reader(['en'], gpu=True)
    sct = mss.mss()
    overlay = StrikeOverlay()
    
    clicked_recently = {} 

    print(f"--- COMPETITIVE MODE ACTIVE ---")
    print(f"OCR optimized for speed. Monitoring list...")

    try:
        while True:
            # 1. Ultra-Fast Capture
            sct_img = sct.grab(capture_region)
            img = np.array(sct_img)
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            _, thresh = cv2.threshold(gray, 185, 255, cv2.THRESH_BINARY)
            
            # 2. Optimized OCR Call (Allowlist speeds this up by ~30-50%)
            results = reader.readtext(
                thresh, 
                detail=0, 
                allowlist='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ '
            )
            
            for text in results:
                if len(text) < 3: continue
                
                # 3. High-Strict Match (92%) to avoid clicking words stolen by others
                match, score = process.extractOne(text, master_dict.keys())
                
                if score >= 92:
                    last_click = clicked_recently.get(match, 0)
                    if time.time() - last_click < 2.5: continue
                    
                    target_x, target_y = master_dict[match]
                    
                    # 4. Human-Speed Injection
                    # Add a micro-delay based on reaction settings
                    delay = random.uniform(*HUMAN_REACTION_RANGE)
                    time.sleep(delay)
                    
                    # Tap
                    off_x = random.randint(-HUMAN_CLICK_OFFSET, HUMAN_CLICK_OFFSET)
                    off_y = random.randint(-HUMAN_CLICK_OFFSET, HUMAN_CLICK_OFFSET)
                    
                    overlay.update(f"STRIKE: {match}")
                    print(f"[FAST-STRIKE] {match} (Score: {score})")
                    
                    device.shell(f"input tap {target_x + off_x} {target_y + off_y}")
                    clicked_recently[match] = time.time()
                    
                    # Cooldown
                    time.sleep(random.uniform(*SUCCESS_COOLDOWN))
                    overlay.update("Watching...")

            overlay.root.update()
            # No sleep here for maximum frequency

    except KeyboardInterrupt:
        overlay.root.destroy()
        print("Stopped.")

if __name__ == "__main__":
    main()
