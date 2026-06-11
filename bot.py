import time
import random
import cv2
import sys
import numpy as np
import easyocr
import mss
import mss.tools
from ppadb.client import Client as AdbClient
from thefuzz import process, fuzz
import json
import os
import ast
import tkinter as tk
import ctypes

# Force Windows to treat this app as High DPI-aware so coordinates match physical pixels for mss.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

from tkinter import simpledialog
import re
import threading
import queue
import glob
from enum import Enum
from mapper_ui import PostRoundMapper

class GameState(Enum):
    WAITING_FOR_STAGE = 1
    PLAYING = 2
    MAPPING = 3
    PAUSED = 4

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
    def __init__(self, on_round_over, on_pause_toggle, on_recalibrate, region, is_multiplayer=False, speed_settings=None):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.9)
        
        height = 70 if is_multiplayer else 35
        self.root.geometry(f"750x{height}+{region['left'] + region['width'] + 20}+{region['top']}")
        
        self.top_frame = tk.Frame(self.root, bg="#121212")
        self.top_frame.pack(fill="both", expand=True)
        
        self.status_text = "Bot Active"
        self.label = tk.Label(self.top_frame, text=self.status_text, bg="#121212", fg="#00ff00", font=("Arial", 9, "bold"))
        self.label.pack(side="left", fill="both", expand=True, padx=2)
        
        self.mode_var = tk.StringVar(value="Click Mode")
        self.mode_dropdown = tk.OptionMenu(self.top_frame, self.mode_var, "Click Mode", "Visual Mode")
        self.mode_dropdown.config(bg="#2196F3", fg="white", relief="flat", font=("Arial", 8))
        self.mode_dropdown.pack(side="left", padx=2)
        
        self.force_start = False
        def on_force_start():
            self.force_start = True
            
        self.force_btn = tk.Button(self.top_frame, text="Force Start", command=on_force_start, bg="#9C27B0", fg="white", relief="flat", font=("Arial", 8))
        self.force_btn.pack(side="left", padx=2)
        
        self.recal_btn = tk.Button(self.top_frame, text="Recalibrate", command=on_recalibrate, bg="#3F51B5", fg="white", relief="flat", font=("Arial", 8))
        self.recal_btn.pack(side="left", padx=2)
        
        def on_main_menu():
            import sys, subprocess, os
            subprocess.Popen([sys.executable] + sys.argv)
            os._exit(0)
            
        self.menu_btn = tk.Button(self.top_frame, text="Main Menu", command=on_main_menu, bg="#607D8B", fg="white", relief="flat", font=("Arial", 8))
        self.menu_btn.pack(side="right", padx=2)
        
        self.pause_btn = tk.Button(self.top_frame, text="Pause", command=on_pause_toggle, bg="#FF9800", fg="white", relief="flat", font=("Arial", 8))
        self.pause_btn.pack(side="right", padx=2)
        
        self.end_btn = tk.Button(self.top_frame, text="End Round", command=on_round_over, bg="#F44336", fg="white", relief="flat", font=("Arial", 8))
        self.end_btn.pack(side="right", padx=2)
        
        if is_multiplayer and speed_settings:
            self.bottom_frame = tk.Frame(self.root, bg="#121212")
            self.bottom_frame.pack(fill="both", expand=True)
            
            tk.Label(self.bottom_frame, text="Co-Op Speed:", bg="#121212", fg="#00ff00", font=("Arial", 8, "bold")).pack(side="left", padx=2)
            
            self.speed_mode_var = tk.StringVar(value=speed_settings.get("mode", "athlete"))
            self.speed_dropdown = tk.OptionMenu(self.bottom_frame, self.speed_mode_var, "human", "athlete", "custom")
            self.speed_dropdown.config(bg="#FF9800", fg="white", relief="flat", font=("Arial", 8))
            self.speed_dropdown.pack(side="left", padx=2)
            
            self.custom_speed_var = tk.StringVar(value=speed_settings.get("custom", "0.01"))
            self.custom_speed_entry = tk.Entry(self.bottom_frame, textvariable=self.custom_speed_var, width=6, bg="#333", fg="white", font=("Arial", 8))
            self.custom_speed_entry.pack(side="left", padx=2)
            
            def on_speed_change(*args):
                speed_settings["mode"] = self.speed_mode_var.get()
                speed_settings["custom"] = self.custom_speed_var.get()
                
            self.speed_mode_var.trace_add("write", on_speed_change)
            self.custom_speed_var.trace_add("write", on_speed_change)
        
        # Transparent ESP Window
        self.esp = tk.Toplevel(self.root)
        self.esp.overrideredirect(True)
        self.esp.attributes("-topmost", True)
        self.esp.attributes("-transparentcolor", "black")
        self.esp.geometry(f"{region['width']}x{region['height']}+{region['left']}+{region['top']}")
        
        self.esp_canvas = tk.Canvas(self.esp, bg="black", highlightthickness=0)
        self.esp_canvas.pack(fill="both", expand=True)
        
        self.root.update()

    def update_text(self, text):
        self.status_text = text
        
    def draw_esp_markers(self, markers):
        # Draw on main thread safely
        self.root.after(0, self._draw_esp, markers)
        
    def _draw_esp(self, markers):
        self.esp_canvas.delete("all")
        for (x, y, word) in markers:
            # Draw a small hollow cyan circle
            r = 15
            self.esp_canvas.create_oval(x-r, y-r, x+r, y+r, outline="#00FFFF", width=3)
            # Draw text label below the circle with a dark outline for visibility
            self.esp_canvas.create_text(x, y+25, text=word, fill="black", font=("Arial", 11, "bold"))
            self.esp_canvas.create_text(x, y+25, text=word, fill="#00FFFF", font=("Arial", 10, "bold"))
            
    def refresh(self):
        self.label.config(text=self.status_text)
        self.root.update()

class BotLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dreamscape Bot Launcher")
        self.root.minsize(450, 750)
        self.root.configure(bg="#2b2b2b")
        self.result = None
        
        self.refresh_profiles()
        self.selected_profile = tk.StringVar(value=self.profiles[0] if self.profiles else "")
        self.mode = tk.StringVar(value="single")
        
        # Speed mode vars
        self.speed_mode = tk.StringVar(value="athlete")
        self.custom_speed = tk.StringVar(value="0.01")
        
        self.setup_ui()
        self.root.mainloop()
        
    def refresh_profiles(self):
        self.profiles = [os.path.basename(p).replace('.json', '') for p in glob.glob("profiles/*.json")]
        
    def setup_ui(self):
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
            
        tk.Label(self.root, text="Dreamscape Bot", fg="#00ff00", bg="#2b2b2b", font=("Arial", 18, "bold")).pack(pady=10)
        
        # Profile Section
        frame_prof = tk.Frame(self.root, bg="#2b2b2b")
        frame_prof.pack(pady=10, fill="x", padx=20)
        tk.Label(frame_prof, text="Select Profile:", fg="white", bg="#2b2b2b", font=("Arial", 12)).pack(anchor="w")
        
        if self.profiles:
            dropdown = tk.OptionMenu(frame_prof, self.selected_profile, *self.profiles)
            dropdown.config(width=20, bg="#444", fg="white", highlightthickness=0)
            dropdown.pack(side="left", pady=5)
        else:
            tk.Label(frame_prof, text="No profiles found.", fg="red", bg="#2b2b2b").pack(side="left")
            
        tk.Button(frame_prof, text="Create New", command=self.create_profile, bg="#2196F3", fg="white").pack(side="right", pady=5)
        
        # Mode Section
        tk.Label(self.root, text="Select Game Mode:", bg="#2b2b2b", fg="white", font=("Arial", 12)).pack(anchor="w", pady=(10,0))
        
        frame_mode = tk.Frame(self.root, bg="#2b2b2b")
        frame_mode.pack(fill="x", pady=5, padx=10)
        
        tk.Radiobutton(frame_mode, text="Single Player (Companion Mode)", variable=self.mode, value="single", bg="#2b2b2b", fg="white", selectcolor="#444", command=self.update_ui_state).pack(anchor="w")
        tk.Radiobutton(frame_mode, text="Multiplayer (Speed Mode)", variable=self.mode, value="multi", bg="#2b2b2b", fg="white", selectcolor="#444", command=self.update_ui_state).pack(anchor="w")
        
        # Speed Settings Frame (only visible in multiplayer)
        self.frame_speed = tk.Frame(self.root, bg="#333", padx=10, pady=5)
        
        tk.Label(self.frame_speed, text="Speed Setting:", bg="#333", fg="#00ff00", font=("Arial", 10, "bold")).pack(anchor="w")
        
        tk.Radiobutton(self.frame_speed, text="Slow Human (1.0 - 2.5s)", variable=self.speed_mode, value="slow_human", bg="#333", fg="white", selectcolor="#555", command=self.update_ui_state).pack(anchor="w")
        tk.Radiobutton(self.frame_speed, text="Human (0.4 - 1.2s)", variable=self.speed_mode, value="human", bg="#333", fg="white", selectcolor="#555", command=self.update_ui_state).pack(anchor="w")
        tk.Radiobutton(self.frame_speed, text="Athlete (0.05 - 0.25s)", variable=self.speed_mode, value="athlete", bg="#333", fg="white", selectcolor="#555", command=self.update_ui_state).pack(anchor="w")
        
        frame_custom = tk.Frame(self.frame_speed, bg="#333")
        frame_custom.pack(anchor="w", fill="x")
        tk.Radiobutton(frame_custom, text="Custom (seconds):", variable=self.speed_mode, value="custom", bg="#333", fg="white", selectcolor="#555", command=self.update_ui_state).pack(side="left")
        
        self.custom_speed_entry = tk.Entry(frame_custom, textvariable=self.custom_speed, width=6, bg="#555", fg="white")
        
        # Action Buttons (Rename, Export)
        self.frame_actions = tk.Frame(self.root, bg="#2b2b2b")
        self.frame_actions.pack(fill="x", pady=5)
        tk.Button(self.frame_actions, text="Rename Map", command=self.rename_profile, bg="#FF9800", fg="white", font=("Arial", 10, "bold")).pack(side="left", expand=True, fill="x", padx=5)
        tk.Button(self.frame_actions, text="Export Map", command=self.export_profile, bg="#9C27B0", fg="white", font=("Arial", 10, "bold")).pack(side="left", expand=True, fill="x", padx=5)
        
        frame_actions2 = tk.Frame(self.root, bg="#2b2b2b")
        frame_actions2.pack(fill="x", pady=5)
        tk.Button(frame_actions2, text="Open Map Editor", command=self.open_map_editor, bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side="left", expand=True, fill="x", padx=5)
        tk.Button(frame_actions2, text="Delete Map", command=self.delete_profile, bg="#F44336", fg="white", font=("Arial", 10, "bold")).pack(side="left", expand=True, fill="x", padx=5)
        
        # Image Preview
        self.preview_lbl = tk.Label(self.root, text="No Preview Available\n(Play round to auto-generate)", bg="black", fg="white", width=40, height=10)
        self.preview_lbl.pack(pady=10)
        
        # Bind the preview update to the dropdown
        self.selected_profile.trace_add("write", self.update_preview)
        
        # Start Button
        launch_btn = tk.Button(self.root, text="LAUNCH BOT", font=("Arial", 16, "bold"), bg="#4CAF50", fg="white", command=self.start_bot)
        launch_btn.pack(pady=15)
        
        # Initial call
        self.update_preview()
        self.update_ui_state()
        
    def update_ui_state(self, *args):
        # Show/Hide Speed settings based on game mode
        if self.mode.get() == "multi":
            self.frame_speed.pack(fill="x", padx=10, pady=5)
            # Re-pack the rest of the elements so they stay below it
            # To do this cleanly, we can just let Tkinter naturally order them by repacking everything below it.
            # But the easiest way is to use the 'before' or 'after' parameter.
            # We want frame_speed to be after frame_mode.
            # However, since frame_actions is right below it, we can pack it before frame_actions!
            self.frame_speed.pack(before=self.frame_actions, fill="x", padx=10, pady=5)
        else:
            self.frame_speed.pack_forget()
            
        # Enable/Disable custom speed entry
        if self.speed_mode.get() == "custom":
            self.custom_speed_entry.pack(side="left", padx=5)
        else:
            self.custom_speed_entry.pack_forget()

    def update_preview(self, *args):
        prof = self.selected_profile.get()
        if not prof: return
        img_path = os.path.join("profiles", prof + ".png")
        if os.path.exists(img_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(img_path)
                img.thumbnail((350, 350))
                self.preview_img = ImageTk.PhotoImage(img)
                self.preview_lbl.config(image=self.preview_img, text="", width=350, height=350)
            except: pass
        else:
            self.preview_img = None
            self.preview_lbl.config(image="", text="No Preview Available\n(Play round to auto-generate)", width=40, height=10)

    def rename_profile(self):
        old_name = self.selected_profile.get()
        if not old_name: return
        new_name = simpledialog.askstring("Rename", f"Rename '{old_name}' to:", parent=self.root)
        if new_name:
            new_name = new_name.lower().strip()
            old_json = os.path.join("profiles", old_name + ".json")
            new_json = os.path.join("profiles", new_name + ".json")
            old_png = os.path.join("profiles", old_name + ".png")
            new_png = os.path.join("profiles", new_name + ".png")
            
            try: os.rename(old_json, new_json)
            except: pass
            try: os.rename(old_png, new_png)
            except: pass
            
            self.refresh_profiles()
            self.selected_profile.set(new_name)
            self.setup_ui()
            
    def delete_profile(self):
        prof = self.selected_profile.get()
        if not prof: return
        from tkinter import messagebox
        if messagebox.askyesno("Delete Map", f"Are you sure you want to completely delete '{prof}'?"):
            try: os.remove(os.path.join("profiles", prof + ".json"))
            except: pass
            try: os.remove(os.path.join("profiles", prof + ".png"))
            except: pass
            self.refresh_profiles()
            if self.profiles:
                self.selected_profile.set(self.profiles[0])
            else:
                self.selected_profile.set("")
            self.setup_ui()
            
    def open_map_editor(self):
        prof = self.selected_profile.get()
        if not prof: return
        
        json_path = os.path.join("profiles", prof + ".json")
        img_path = os.path.join("profiles", prof + ".png")
        
        from tkinter import messagebox
        if not os.path.exists(json_path) or not os.path.exists(img_path):
            messagebox.showerror("Error", "You need a baseline image to map items. Play a round with this profile first to generate it!")
            return
            
        from mapper_ui import PostRoundMapper
        
        # Hide the launcher so the editor is the only visible window
        self.root.withdraw()
        
        def on_complete(new_coords):
            self.root.deiconify()
            self.setup_ui()
            
        # Passing empty list for unknown_words, the editor will load mapped targets from JSON
        PostRoundMapper(json_path, img_path, [], 1080, 2400, on_complete, master=self.root)
            
    def export_profile(self):
        prof = self.selected_profile.get()
        if not prof: return
        
        json_path = os.path.join("profiles", prof + ".json")
        img_path = os.path.join("profiles", prof + ".png")
        
        from tkinter import messagebox
        if not os.path.exists(json_path) or not os.path.exists(img_path):
            messagebox.showerror("Error", "Need both JSON and PNG to export. Play a round first to save the PNG!")
            return
            
        import cv2
        import numpy as np
        img = cv2.imread(img_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
            coords = data.get("coordinates", {})
            
        h, w = img.shape[:2]
        
        # Extend the image to the right to create a clean Legend Panel
        panel_width = 350
        out_img = np.full((h, w + panel_width, 3), 255, dtype=np.uint8)
        out_img[0:h, 0:w] = img
        
        word_list = []
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        
        legend_x = w + 20
        legend_y = 40
        
        # Sort items Left-to-Right to make it incredibly easy to find them!
        sorted_coords = sorted(coords.items(), key=lambda item: item[1][0])
        
        # Vibrant colors for grouping
        colors = [
            (0, 0, 255),    # Red (1-5)
            (255, 0, 0),    # Blue (6-10)
            (0, 128, 0),    # Green (11-15)
            (204, 0, 204),  # Purple (16-20)
            (0, 165, 255),  # Orange (21-25)
            (0, 255, 255)   # Yellow (26-30)
        ]
        
        for idx, (word, pct) in enumerate(sorted_coords, 1):
            px, py = int(pct[0] * w), int(pct[1] * h)
            
            group_idx = (idx - 1) // 5
            color = colors[group_idx % len(colors)]
            
            # Map Marker
            radius = 16
            cv2.circle(out_img, (px, py), radius, color, -1)
            cv2.circle(out_img, (px, py), radius, (255, 255, 255), 2)
            
            # Perfect Centering Math for Number
            text = str(idx)
            text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
            tx = px - (text_size[0] // 2)
            ty = py + (text_size[1] // 2)
            cv2.putText(out_img, text, (tx, ty), font, font_scale, (255, 255, 255), thickness)
            
            # Legend Entry with Matching Color
            entry_text = f"{idx}. {word}"
            cv2.putText(out_img, entry_text, (legend_x, legend_y), font, 0.55, color, 2)
            cv2.putText(out_img, entry_text, (legend_x, legend_y), font, 0.55, (0, 0, 0), 1)
            legend_y += 35
            
            # Wrap to next column if legend gets too tall
            if legend_y > h - 20:
                legend_x += 160
                legend_y = 40
            
            word_list.append(entry_text)
            
        os.makedirs("profiles/exported", exist_ok=True)
        export_path = f"profiles/exported/{prof}_labeled.png"
        cv2.imwrite(export_path, out_img)
        
        # Copy to clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(word_list))
        
        messagebox.showinfo("Export Success", f"Map exported to {export_path}\n\nWord list copied to clipboard!")
            
    def on_calibrate(self):
        self.root.destroy()
        import subprocess
        subprocess.run(["python", "region_selector.py"])
        self.result = None

    def create_profile(self):
        new_name = simpledialog.askstring("New Profile", "Enter a name for the new map profile:", parent=self.root)
        if new_name:
            new_name = new_name.lower().strip()
            path = os.path.join("profiles", f"{new_name}.json")
            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump({"targets": [], "coordinates": {}}, f, indent=4)
            self.refresh_profiles()
            self.selected_profile.set(new_name)
            self.setup_ui()
            
    def start_bot(self):
        if not self.selected_profile.get():
            return
        speed_settings = {
            "mode": self.speed_mode.get(),
            "custom": self.custom_speed.get()
        }
        self.result = (self.selected_profile.get(), self.mode.get(), speed_settings)
        self.root.destroy()

def get_scrcpy_rect():
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, 'Dreamscape Scrcpy')
    if not hwnd: return None
    
    # Bring the window to the absolute front so mss doesn't capture VS Code/Terminal!
    try:
        user32.ShowWindow(hwnd, 5) # SW_SHOW
        user32.SetForegroundWindow(hwnd)
    except:
        pass
    
    client_rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(client_rect))
    
    point = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    
    return {
        "top": point.y,
        "left": point.x,
        "width": client_rect.right,
        "height": client_rect.bottom
    }

def main():
    import urllib.request
    
    # Load or download the master English dictionary for filtering junk words
    if not os.path.exists("english_words.txt"):
        print("Downloading dictionary for junk word filtering...")
        urllib.request.urlretrieve("https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt", "english_words.txt")
        
    with open("english_words.txt", "r") as f:
        global_words = set(f.read().splitlines())
        
    # Also inject anything we've mapped previously just to be safe
    for profile in os.listdir("profiles"):
        if profile.endswith(".json"):
            with open(os.path.join("profiles", profile), "r") as f:
                try:
                    pdata = json.load(f).get("coordinates", {})
                    for key in pdata:
                        for word_part in key.split():
                            global_words.add(word_part.lower())
                except: pass
                
    launcher = BotLauncher()
    if not launcher.result:
        print("Launcher closed. Exiting.")
        return
        
    profile_name, game_mode, speed_settings = launcher.result
    is_multiplayer = (game_mode == 'multi')
    
    profile_path = os.path.join("profiles", f"{profile_name}.json")
    with open(profile_path, "r") as f:
        data = json.load(f)
        master_dict = data.get("coordinates", {})
    
    # Auto-Track Scrcpy Window
    scrcpy_rect = get_scrcpy_rect()
    if not scrcpy_rect:
        print("Error: Could not find 'Dreamscape Scrcpy' window! Please open it first.")
        return
        
    capture_region_full = scrcpy_rect
    print(f"Auto-Tracked Game Window: {capture_region_full}")
    
    # We will initialize the OCR region to full screen. 
    # It dynamically calibrates and shrinks itself the moment it detects game words!
    capture_region_ocr = dict(capture_region_full)

    client = AdbClient(host="127.0.0.1", port=5037)
    devices = client.devices()
    if not devices:
        print("Error: No ADB devices found! Ensure your phone is connected and USB debugging is enabled.")
        return
        
    target_serial = None
    try:
        with open("bot_settings.json", "r") as f:
            settings = json.load(f)
            target_serial = settings.get("adb_ip")
    except:
        pass
        
    device = None
    if target_serial:
        for d in devices:
            if d.serial == target_serial:
                device = d
                break
                
    if not device:
        device = devices[0]
        
    print(f"Connected to ADB Device: {device.serial}")
    
    wm_size = device.shell("wm size")
    res_match = re.search(r'(\d+)x(\d+)', wm_size)
    if res_match:
        adb_w, adb_h = int(res_match.group(1)), int(res_match.group(2))
        print(f"Detected Device Resolution: {adb_w}x{adb_h}")
    else:
        adb_w, adb_h = 1080, 1920
    
    reader = easyocr.Reader(['en'], gpu=True)
    sct = mss.mss()
    
    # State Machine Vars
    current_state = GameState.WAITING_FOR_STAGE
    round_unknowns = set()
    saw_intro = False
    consecutive_empty = 0
    last_continue_scan = time.time()
    total_time = 60
    round_start_time = time.time()
    baseline_taken = False
    
    def on_round_over():
        nonlocal current_state
        if current_state != GameState.MAPPING:
            current_state = GameState.MAPPING
    def on_pause_toggle():
        nonlocal current_state
        if current_state == GameState.PLAYING:
            current_state = GameState.PAUSED
            overlay.pause_btn.config(text="Resume")
        elif current_state == GameState.PAUSED:
            current_state = GameState.PLAYING
            overlay.pause_btn.config(text="Pause")

    def is_valid_item(text_to_check):
        # Must be mostly letters and every word must exist in the dictionary
        clean_text = text_to_check.strip().lower()
        if not clean_text: return False
        
        parts = clean_text.split()
        for p in parts:
            # Remove minor punctuation for checking
            p_clean = ''.join(c for c in p if c.isalpha())
            if len(p_clean) < 2 or p_clean not in global_words:
                return False
        return True
            
    def on_recalibrate():
        nonlocal capture_region_full, capture_region_ocr
        new_rect = get_scrcpy_rect()
        if new_rect:
            capture_region_full = new_rect
            capture_region_ocr = dict(capture_region_full)
            height = 70 if is_multiplayer else 35
            overlay.root.geometry(f"750x{height}+{new_rect['left'] + new_rect['width'] + 20}+{new_rect['top']}")
            overlay.esp.geometry(f"{new_rect['width']}x{new_rect['height']}+{new_rect['left']}+{new_rect['top']}")
            overlay.update_text("Window Recalibrated!")
            overlay.refresh()
            print(f"Recalibrated Scrcpy Tracking: {capture_region_full}")

    overlay = StrikeOverlay(on_round_over, on_pause_toggle, on_recalibrate, capture_region_full, is_multiplayer, speed_settings)
    clicked_recently = {}
    last_global_click = 0.0

    print(f"--- {'MULTIPLAYER' if is_multiplayer else 'SINGLE PLAYER COMPANION'} MODE ACTIVE ---")
    print(f"Loaded Map: {profile_name}")

    try:
        while True:
            if current_state == GameState.WAITING_FOR_STAGE:
                # Detect Stage Intro by scanning the full screen
                sct_img = sct.grab(capture_region_full)
                img = np.array(sct_img)
                gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                
                # Display Live Debug for Intro Detection
                cv2.namedWindow("Bot Vision Debug")
                cv2.moveWindow("Bot Vision Debug", capture_region_full["left"] + capture_region_full["width"] + 50, 100)
                cv2.imshow("Bot Vision Debug", cv2.resize(gray, (0,0), fx=0.4, fy=0.4))
                cv2.waitKey(1)
                
                res = reader.readtext(gray, detail=0)
                text_str = " ".join([t.lower() for t in res])
                
                if overlay.force_start:
                    overlay.force_start = False
                    overlay.update_text("FORCE STARTED ROUND!")
                    current_state = GameState.PLAYING
                    saw_intro = False
                    round_start_time = time.time()
                    baseline_taken = False
                    capture_region_ocr = dict(capture_region_full)
                    total_time = 60
                    round_unknowns.clear()
                    next_global_delay = 0.0
                    print("Force Started.")
                elif is_multiplayer and "start timer" in text_str:
                    total_time = 60
                    overlay.update_text("Waiting for Co-op Start...")
                    saw_intro = True
                    consecutive_empty = 0
                elif not is_multiplayer and "tap" in text_str and "anywhere" in text_str:
                    # Look for any 2-digit number optionally followed by s, 5, or 3 (OCR mistakes)
                    matches = re.finditer(r'\b(\d{2})\s*[sS53]?\b', text_str)
                    total_time = 60
                    
                    for m in matches:
                        val = int(m.group(1))
                        # Timers are generally 30-99 seconds. This filters out Stage numbers (e.g. 12-5)
                        if 25 <= val <= 99:
                            total_time = val
                            break
                            
                    overlay.update_text(f"Waiting for you to click Start... ({total_time}s)")
                    saw_intro = True
                    consecutive_empty = 0
                elif saw_intro:
                    if is_multiplayer:
                        # 0-Millisecond Start Detection: Check if the screen shade lifted!
                        h, w = gray.shape
                        bottom_crop = gray[int(h*0.7):, :]
                        _, wait_thresh = cv2.threshold(bottom_crop, 200, 255, cv2.THRESH_BINARY)
                        
                        # Wait for the text pixels at the bottom to become bright white
                        white_pixels = cv2.countNonZero(wait_thresh)
                        if white_pixels > 200:
                            pass # Shade lifted! We drop down to transition.
                        else:
                            overlay.update_text("Waiting for Shade to Lift...")
                            overlay.refresh()
                            continue
                    else:
                        consecutive_empty += 1
                        if consecutive_empty < 3:
                            overlay.update_text("Preparing Start...")
                            overlay.refresh()
                            time.sleep(0.5)
                            continue
                        
                    overlay.update_text(f"ROUND STARTED! ({total_time}s)")
                    current_state = GameState.PLAYING
                    saw_intro = False
                    consecutive_empty = 0
                    round_start_time = time.time()
                    baseline_taken = False
                    capture_region_ocr = dict(capture_region_full)
                    next_global_delay = 0.0
                    
                    round_unknowns.clear()
                    print(f"Started playing with a {total_time}s timer.")
                elif is_multiplayer:
                    overlay.update_text("Waiting for Co-op Lobby...")
                else:
                    overlay.update_text("Waiting for Stage Intro...")
                    
                overlay.refresh()
                time.sleep(0.5)

            elif current_state == GameState.PLAYING:
                # 1. Background Auto-Continue Scan (Every 2 seconds)
                if time.time() - last_continue_scan > 2.0:
                    last_continue_scan = time.time()
                    full_sct = sct.grab(capture_region_full)
                    full_gray = cv2.cvtColor(np.array(full_sct), cv2.COLOR_BGRA2GRAY)
                    
                    # Resize by 50% to make the OCR 4x faster!
                    # This prevents the bot from "pausing" or lagging while checking for the victory screen.
                    small_gray = cv2.resize(full_gray, (0,0), fx=0.5, fy=0.5)
                    full_res = reader.readtext(small_gray, detail=0)
                    
                    full_text = " ".join([t.lower() for t in full_res])
                    if "continue" in full_text or "claim" in full_text or "timer up" in full_text or "all items found" in full_text or "team room" in full_text:
                        print("Detected Victory Screen (Continue/Claim/Timer Up/All Items Found/Team Room). Auto Round Over!")
                        on_round_over()
                        continue
                        
                # 2. Fast OCR for Items
                sct_img = sct.grab(capture_region_ocr)
                img = np.array(sct_img)
                
                gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                # Binarize text to solid white (200 threshold prevents eroding anti-aliased text edges)
                _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
                
                # Display Live Debug for OCR Region
                cv2.namedWindow("Bot Vision Debug")
                cv2.moveWindow("Bot Vision Debug", capture_region_full["left"] + capture_region_full["width"] + 50, 100)
                cv2.imshow("Bot Vision Debug", thresh)
                cv2.waitKey(1)
                
                if not baseline_taken:
                    # Calibration mode: use detail=1 to get bounding boxes
                    results_raw = reader.readtext(thresh, detail=1, allowlist='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ')
                    
                    valid_bboxes = []
                    valid_words = []
                    for bbox, text, conf in results_raw:
                        clean = text.strip().title()
                        if is_valid_item(clean):
                            # Ensure it's in the bottom half of the current search area
                            y_center = (bbox[0][1] + bbox[2][1]) / 2
                            if y_center > capture_region_ocr["height"] * 0.5:
                                valid_bboxes.append(bbox)
                                valid_words.append(clean)
                                
                    if len(valid_bboxes) > 0:
                        y_mins = [min(p[1] for p in bbox) for bbox in valid_bboxes]
                        y_maxs = [max(p[1] for p in bbox) for bbox in valid_bboxes]
                        min_y = int(min(y_mins))
                        max_y = int(max(y_maxs))
                        pad = 15
                        
                        capture_region_ocr = {
                            "top": capture_region_ocr["top"] + min_y - pad,
                            "left": capture_region_full["left"],
                            "width": capture_region_full["width"],
                            "height": (max_y - min_y) + (pad * 2)
                        }
                        print(f"🎯 Dynamic OCR Calibrated: {capture_region_ocr}")
                        overlay.update_text(f"OCR Bound Set! ({len(valid_words)} items)")
                        
                        # Set baseline taken immediately after finding words
                        import shutil
                        import datetime
                        os.makedirs("profiles/archive", exist_ok=True)
                        sct_img_full = sct.grab(capture_region_full)
                        cv2.imwrite("baseline.png", np.array(sct_img_full))
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        try: shutil.copy("baseline.png", f"profiles/archive/{profile_name}_{timestamp}.png")
                        except: pass
                        baseline_taken = True
                        print("Instant baseline screenshot saved perfectly on UI load!")
                        
                    results = valid_words
                else:
                    results_raw = reader.readtext(thresh, detail=0, allowlist='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ')
                    results = [t.strip().title() for t in results_raw if is_valid_item(t.strip().title())]
                
                current_mode = overlay.mode_var.get()
                esp_markers = []
                
                for text in results:
                    text = text.strip()
                    if not text: continue
                    
                    match, score = process.extractOne(text, master_dict.keys()) if master_dict else (text, 0)
                    
                    if score >= 89:
                        # WRatio falsely inflates scores for very short targets (e.g., 'A', 'X') matched against long OCR strings.
                        if len(match) <= 2:
                            # We tolerate up to 2 characters of OCR noise (e.g., 'A.', '|A'), but block massive false positives (like 'Apple')
                            if len(text) > len(match) + 2:
                                continue
                            if match.lower() not in text.lower():
                                continue
                                
                        pct_x, pct_y = master_dict[match]
                        
                        # For ESP we need coordinates relative to the scrcpy window size
                        esp_x = int(pct_x * capture_region_full["width"])
                        esp_y = int(pct_y * capture_region_full["height"])
                        esp_markers.append((esp_x, esp_y, match))
                        
                        if current_mode == "Visual Mode":
                            continue # Skip all clicking logic
                            
                        last_click = clicked_recently.get(match, 0)
                        
                        if is_multiplayer:
                            # 0-Queue Policy, direct click with custom speed delay
                            if time.time() - last_click < 2.5: continue
                            
                            target_x = int(pct_x * adb_w)
                            target_y = int(pct_y * adb_h)
                            
                            # Extremely tight spread
                            off_x = random.randint(-2, 2)
                            off_y = random.randint(-2, 2)
                            
                            overlay.update_text(f"CO-OP STRIKE: {match}")
                            
                            if time.time() - last_global_click < next_global_delay:
                                continue # Keep scanning while waiting for global cooldown!
                                
                            target_x = int(pct_x * adb_w)
                            target_y = int(pct_y * adb_h)
                            
                            # Extremely tight spread
                            off_x = random.randint(-2, 2)
                            off_y = random.randint(-2, 2)
                            
                            overlay.update_text(f"CO-OP STRIKE: {match}")
                            
                            overlay.refresh()
                            if current_state != GameState.PLAYING:
                                break
                                
                            device.shell(f"input tap {target_x + off_x} {target_y + off_y}")
                            clicked_recently[match] = time.time()
                            last_global_click = time.time()
                            
                            actual_delay = next_global_delay
                            
                            # Generate NEXT delay using Normal (Gaussian) Distribution!
                            # This creates a bell curve where most clicks cluster near the base delay,
                            # but occasionally have wider deviations (like a real human losing focus).
                            if speed_settings["mode"] == "slow_human":
                                next_global_delay = max(0.5, random.gauss(1.6, 0.4))
                            elif speed_settings["mode"] == "human":
                                next_global_delay = max(0.4, random.gauss(0.8, 0.25))
                            elif speed_settings["mode"] == "athlete":
                                next_global_delay = max(0.05, random.gauss(0.15, 0.05))
                            else:
                                try:
                                    base_delay = float(speed_settings["custom"])
                                    next_global_delay = max(0.05, random.gauss(base_delay, base_delay * 0.25))
                                except:
                                    next_global_delay = 0.05
                                    
                            print(f"[CO-OP STRIKE] {match} -> Click: {target_x + off_x}, {target_y + off_y} (Cooldown: {actual_delay:.3f}s)")
                            break
                        else:
                            # V3 Single Player Direct-Click Logic
                            # 8s cooldown prevents double-clicking greyed-out items while waiting for the page to flip
                            if time.time() - last_click < 8.0: continue
                            
                            target_x = int(pct_x * adb_w)
                            target_y = int(pct_y * adb_h)
                            
                            if HUMAN_CLICK_OFFSET > 0:
                                off_x = random.randint(-3, 3) # Extremely tight spread to prevent misses
                                off_y = random.randint(-3, 3)
                            else:
                                off_x, off_y = 0, 0
                                
                            overlay.update_text(f"STRIKE: {match}")
                            print(f"[FAST-STRIKE] {match} (Score: {score}) -> Click: {target_x + off_x}, {target_y + off_y}")
                            
                            time_left = total_time - (time.time() - round_start_time)
                            if time_left > 20:
                                delay = random.uniform(0.7, 1.8)
                            else:
                                delay = random.uniform(0.1, 0.3)
                                
                            time.sleep(delay)
                            
                            # Process any pending UI events (like the user clicking Pause)
                            overlay.refresh()
                            if current_state != GameState.PLAYING:
                                break # Abort tap if bot was paused during the delay!
                                
                            device.shell(f"input tap {target_x + off_x} {target_y + off_y}")
                            
                            # Start cooldown exactly when the tap hits the screen
                            clicked_recently[match] = time.time()
                            
                            # Break inner OCR loop to force a completely fresh screen capture!
                            break
                            
                    elif score < 85:
                        if is_valid_item(text):
                            # Auto-capitalization for aesthetics
                            clean_val = " ".join([p.capitalize() for p in text.split()])
                            round_unknowns.add(clean_val)
                            
                # Update visual assist overlay
                if current_mode == "Visual Mode":
                    overlay.draw_esp_markers(esp_markers)
                else:
                    # Clear markers if we switch to click mode
                    overlay.draw_esp_markers([])
                
                overlay.refresh()
                
            elif current_state == GameState.MAPPING:
                overlay.root.withdraw()
                
                def on_mapper_complete(new_dict):
                    nonlocal master_dict, current_state
                    master_dict = new_dict
                    current_state = GameState.WAITING_FOR_STAGE
                    overlay.root.deiconify()
                    overlay.update_text("Waiting for Stage Intro...")
                    
                PostRoundMapper(profile_path, "baseline.png", list(round_unknowns), adb_w, adb_h, on_mapper_complete, master=overlay.root)
                # Fallback safeguard: while Toplevel blocks, we sleep here to avoid burning CPU
                time.sleep(0.5)

            elif current_state == GameState.PAUSED:
                overlay.refresh()
                time.sleep(0.5)

    except KeyboardInterrupt:
        overlay.root.destroy()
        cv2.destroyAllWindows()
        print("Stopped.")

if __name__ == "__main__":
    main()
