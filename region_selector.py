import tkinter as tk
import mss
import mss.tools
from pathlib import Path
import ctypes

# Force Windows to treat this app as High DPI-aware so Tkinter coordinates 
# perfectly match the physical pixels for mss.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

class RegionSelector:
    def __init__(self):
        self.selections = []
        self.labels = ["SELECT ENTIRE GAME AREA", "SELECT OCR LIST AREA (Bottom)"]
        self.current_step = 0
        
        self.run_selector()

    def run_selector(self):
        self.root = tk.Tk()
        self.root.attributes('-alpha', 0.3)
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.configure(background='black')
        self.root.config(cursor="cross")

        self.canvas = tk.Canvas(self.root, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Display Instruction Text
        self.canvas.create_text(
            self.root.winfo_screenwidth() // 2, 50,
            text=self.labels[self.current_step],
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
            "top": top,
            "left": left,
            "width": width,
            "height": height
        })
        
        self.root.destroy()
        self.current_step += 1
        
        if self.current_step < len(self.labels):
            self.run_selector()
        else:
            self.save_and_exit()

    def save_and_exit(self):
        config = {
            "full_game": self.selections[0],
            "ocr_list": self.selections[1]
        }
        
        with open("region.json", 'w') as f:
            json.dump(config, f, indent=4)
        
        print("\nCalibration Complete!")
        print(f"Full Game Area: {config['full_game']}")
        print(f"OCR List Area: {config['ocr_list']}")
        
        # Take debug shots
        with mss.mss() as sct:
            for name, region in config.items():
                sct_img = sct.grab(region)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=f"debug_{name}.png")
                print(f"Saved debug image: debug_{name}.png")

if __name__ == "__main__":
    import json
    RegionSelector()
