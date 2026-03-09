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
        self.root = tk.Tk()
        self.root.attributes('-alpha', 0.3) # Transparent window
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.configure(background='black')
        self.root.config(cursor="cross")

        self.canvas = tk.Canvas(self.root, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Make the canvas slightly transparent but tinted
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        # Allow escaping
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        print("Draw a box over the EXACT text area you want the bot to read.")
        print("Press ESC to cancel without saving.")
        self.root.mainloop()

    def on_button_press(self, event):
        self.start_x = self.root.winfo_pointerx()
        self.start_y = self.root.winfo_pointery()
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=3, fill="gray", stipple="gray50")

    def on_move_press(self, event):
        cur_x, cur_y = (self.root.winfo_pointerx(), self.root.winfo_pointery())
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        self.end_x = self.root.winfo_pointerx()
        self.end_y = self.root.winfo_pointery()
        self.root.destroy()
        
        # Calculate standard coordinates
        left = min(self.start_x, self.end_x)
        top = min(self.start_y, self.end_y)
        width = abs(self.start_x - self.end_x)
        height = abs(self.start_y - self.end_y)
        
        capture_region = {
            "top": top,
            "left": left,
            "width": width,
            "height": height
        }
        
        # Output coordinates to file automatically
        config_path = Path("region.json")
        import json
        with open(config_path, 'w') as f:
            json.dump(capture_region, f, indent=4)
        print(f"\nSaved capture region to: {config_path.absolute()}")
        
        print("\nTaking test screenshot of your selected region to confirm...")
        with mss.mss() as sct:
            sct_img = sct.grab(capture_region)
            output_path = Path("mss_region_debug.png")
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(output_path))
            print(f"Saved precise test screenshot to: {output_path.absolute()}")
            print("\nAutomated setup complete! The bot will now automatically read region.json.")

if __name__ == "__main__":
    RegionSelector()
