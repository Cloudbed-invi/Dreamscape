import tkinter as tk
from tkinter import simpledialog
import mss
import mss.tools
from pathlib import Path
import ctypes
import json
import os

# Force Windows to treat this app as High DPI-aware so Tkinter coordinates 
# perfectly match the physical pixels for mss.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

class RegionSelector:
    def __init__(self):
        self.selections = []
        
        # Load existing config if it exists
        self.config = {}
        if os.path.exists("region.json"):
            try:
                with open("region.json", 'r') as f:
                    self.config = json.load(f)
            except: pass
            
        temp_root = tk.Tk()
        temp_root.withdraw()
        
        choice = simpledialog.askstring(
            "Calibration",
            "Which region do you want to map?\n\n1 - Full Game Area\n2 - Multiplayer OCR Area\n3 - Single-Player OCR Area"
        )
        temp_root.destroy()
        
        if choice == "1":
            self.target_key = "full_game"
            self.label_text = "SELECT ENTIRE GAME AREA"
        elif choice == "2":
            self.target_key = "ocr_list"
            self.label_text = "SELECT MULTIPLAYER OCR AREA"
        elif choice == "3":
            self.target_key = "ocr_list_single"
            self.label_text = "SELECT SINGLE-PLAYER OCR AREA"
        else:
            print("Invalid choice. Exiting.")
            return
            
        self.run_selector()

    def run_selector(self):
        self.root = tk.Tk()
        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        self.root.attributes('-alpha', 0.3)
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.configure(background='black')
        self.root.config(cursor="cross")

        self.canvas = tk.Canvas(self.root, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Display Instruction Text
        self.canvas.create_text(
            self.sw // 2, 50,
            text=self.label_text,
            fill="white", font=("Arial", 24, "bold")
        )

        self.rect = None
        self.start_x = None
        self.start_y = None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        
        self.root.mainloop()

    def on_button_press(self, event):
        self.start_x = self.root.winfo_pointerx()
        self.start_y = self.root.winfo_pointery()
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=3, fill="gray", stipple="gray50")

    def on_move_press(self, event):
        cur_x, cur_y = (self.root.winfo_pointerx(), self.root.winfo_pointery())
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x = self.root.winfo_pointerx()
        end_y = self.root.winfo_pointery()
        
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        width = abs(self.start_x - end_x)
        height = abs(self.start_y - end_y)
        
        self.selections.append({
            "top": round(top / self.sh, 4),
            "left": round(left / self.sw, 4),
            "width": round(width / self.sw, 4),
            "height": round(height / self.sh, 4)
        })
        
        self.root.destroy()
        self.save_and_exit()

    def save_and_exit(self):
        self.config[self.target_key] = self.selections[0]
        
        with open("region.json", 'w') as f:
            json.dump(self.config, f, indent=4)
        
        print(f"\nCalibration Complete for: {self.target_key}")
        print(f"Coordinates: {self.config[self.target_key]}")
        
        with mss.mss() as sct:
            pct_region = self.config[self.target_key]
            real_region = {
                "top": int(pct_region["top"] * self.sh),
                "left": int(pct_region["left"] * self.sw),
                "width": int(pct_region["width"] * self.sw),
                "height": int(pct_region["height"] * self.sh)
            }
            sct_img = sct.grab(real_region)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=f"debug_{self.target_key}.png")
            print(f"Saved debug image: debug_{self.target_key}.png")

if __name__ == "__main__":
    RegionSelector()
