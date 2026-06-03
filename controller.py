import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import os
import sys
import json
import re

class FloatingController:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dreamscape Pro")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.geometry("280x320+50+50")
        self.root.overrideredirect(True)
        
        self.bg_color = "#121212"
        self.accent_color = "#00ff00"
        self.btn_color = "#2a2a2a"
        self.root.configure(bg=self.bg_color)

        # Header (Drag)
        self.header = tk.Label(self.root, text="DREAMSCAPE COMMAND", bg="#1f1f1f", fg=self.accent_color, font=("Segoe UI", 9, "bold"))
        self.header.pack(fill="x")
        self.header.bind("<Button-1>", self.start_move)
        self.header.bind("<B1-Motion>", self.do_move)

        # --- IP SETTINGS ---
        ip_frame = tk.Frame(self.root, bg="#1a1a1a")
        ip_frame.pack(fill="x", pady=5, padx=10)
        
        tk.Label(ip_frame, text="ADB IP:", bg="#1a1a1a", fg="#888888", font=("Segoe UI", 7)).pack(side="left")
        self.ip_var = tk.StringVar(value="192.168.2.11:5555")
        self.ip_entry = tk.Entry(ip_frame, textvariable=self.ip_var, bg="#222222", fg="white", 
                                 insertbackground="white", relief="flat", font=("Consolas", 8), width=15)
        self.ip_entry.pack(side="left", padx=5)
        
        tk.Button(ip_frame, text="🔍", command=self.auto_detect_ip, bg="#333333", fg="white", 
                  relief="flat", font=("Segoe UI", 7)).pack(side="right")

        # Status
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self.root, textvariable=self.status_var, bg=self.bg_color, fg="#888888", font=("Segoe UI", 8)).pack(pady=2)

        # MAIN BUTTONS
        self.create_button("🎯 CALIBRATE WINDOW", self.run_calibrate)
        self.create_button("📸 CAPTURE MAP IMAGE", self.run_capture_map)
        self.create_button("🗺️ MAP LEVEL", self.run_mapper, color="#003366")
        
        self.wordlist_active = False
        self.wordlist_btn = tk.Button(self.root, text="📝 START WORDLIST", command=self.toggle_wordlist, 
                                     bg=self.btn_color, fg="white", font=("Segoe UI", 9), relief="flat", height=1)
        self.wordlist_btn.pack(fill="x", padx=10, pady=3)

        self.bot_active = False
        self.bot_btn = tk.Button(self.root, text="🤖 RUN AUTOMATION", command=self.toggle_bot, 
                                     bg="#004400", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", height=1)
        self.bot_btn.pack(fill="x", padx=10, pady=3)

        # Exit
        tk.Button(self.root, text="EXIT", command=self.root.destroy, bg="#331111", fg="#ff4444", 
                  font=("Segoe UI", 7), relief="flat").pack(side="bottom", fill="x", pady=5)

        self._wordlist_process = None
        self._bot_process = None

        # Settings
        self.reaction_ms = tk.IntVar(value=100)
        self.cooldown_ms = tk.IntVar(value=100)
        self.jitter_px = tk.IntVar(value=4)
        self.randomness = tk.IntVar(value=20)
        
        self.load_settings_from_disk()

    def auto_detect_ip(self):
        self.status_var.set("Scanning for devices...")
        try:
            adb_path = os.path.join("platform-tools", "adb.exe")
            result = subprocess.check_output([adb_path, "devices"]).decode()
            lines = result.strip().split("\n")[1:] # Skip header
            devices = [line.split("\t")[0] for line in lines if "device" in line]
            
            if devices:
                self.ip_var.set(devices[0])
                self.status_var.set(f"Detected: {devices[0]}")
                self.save_settings()
            else:
                messagebox.showwarning("Not Found", "No ADB devices detected. Make sure MuMu is open and USB Debugging is ON.")
                self.status_var.set("Detection failed")
        except Exception as e:
            self.status_var.set("ADB error")

    def create_button(self, text, command, color=None):
        bg = color if color else self.btn_color
        btn = tk.Button(self.root, text=text, command=command, bg=bg, fg="white", 
                        font=("Segoe UI", 9), relief="flat", height=1)
        btn.pack(fill="x", padx=10, pady=3)
        return btn

    def toggle_bot(self):
        if not self.bot_active: self.show_speed_popup()
        else:
            self.bot_active = False
            self.bot_btn.config(text="🤖 RUN AUTOMATION", bg="#004400")
            if self._bot_process: self._bot_process.terminate()
            self.status_var.set("Automation Stopped")

    def show_speed_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Speed Dashboard")
        popup.geometry("300x350")
        popup.attributes("-topmost", True)
        popup.configure(bg="#1a1a1a")
        tk.Label(popup, text="SPEED & RANDOMIZATION", bg="#333333", fg="white", font=("Arial", 10, "bold")).pack(fill="x", pady=(0,10))
        self.create_popup_slider(popup, "Reaction (ms)", self.reaction_ms, 0, 2000)
        self.create_popup_slider(popup, "Cooldown (ms)", self.cooldown_ms, 0, 2000)
        self.create_popup_slider(popup, "Randomness (%)", self.randomness, 0, 100)
        self.create_popup_slider(popup, "Click Jitter (px)", self.jitter_px, 0, 30)
        tk.Button(popup, text="🚀 START NOW", command=lambda: [self.save_settings(), self.start_bot_logic(), popup.destroy()], 
                  bg="#006600", fg="white", font=("Arial", 10, "bold")).pack(fill="x", padx=20, pady=20)

    def start_bot_logic(self):
        self.bot_active = True
        self.bot_btn.config(text="🛑 STOP AUTOMATION", bg="#660000")
        self.status_var.set("Bot Running...")
        self.run_script("bot.py", is_bot=True)

    def create_popup_slider(self, parent, label, var, start, end):
        frame = tk.Frame(parent, bg="#1a1a1a")
        frame.pack(fill="x", padx=20, pady=5)
        tk.Label(frame, text=label, bg="#1a1a1a", fg="#aaaaaa", font=("Arial", 8)).pack(side="left")
        val_label = tk.Label(frame, text=f"{var.get()}", bg="#1a1a1a", fg="#00ff00", font=("Arial", 8))
        val_label.pack(side="right")
        def update_val(val): val_label.config(text=f"{int(float(val))}")
        ttk.Scale(parent, from_=start, to_=end, variable=var, orient="horizontal", command=update_val).pack(fill="x", padx=20)

    def save_settings(self):
        settings = {
            "adb_ip": self.ip_var.get(),
            "reaction": self.reaction_ms.get() / 1000.0,
            "cooldown": self.cooldown_ms.get() / 1000.0,
            "jitter": self.jitter_px.get(),
            "randomness": self.randomness.get() / 100.0
        }
        with open("bot_settings.json", "w") as f: json.dump(settings, f)

    def load_settings_from_disk(self):
        if os.path.exists("bot_settings.json"):
            try:
                with open("bot_settings.json", "r") as f:
                    data = json.load(f)
                    self.ip_var.set(data.get("adb_ip", "192.168.2.11:5555"))
            except: pass

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self.x)
        y = self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{x}+{y}")

    def run_script(self, script_name, is_wordlist=False, is_bot=False):
        def task():
            try:
                proc = subprocess.Popen([sys.executable, script_name])
                if is_wordlist: self._wordlist_process = proc
                if is_bot: self._bot_process = proc
                proc.wait()
            except: pass
        threading.Thread(target=task, daemon=True).start()

    def run_calibrate(self): self.run_script("region_selector.py")
    def run_capture_map(self): self.save_settings(); self.run_script("capture_map.py")
    def run_mapper(self): self.run_script("coordinate_mapper.py")

    def toggle_wordlist(self):
        if not self.wordlist_active:
            self.wordlist_active = True
            self.wordlist_btn.config(text="🛑 STOP WORDLIST", bg="#660000")
            self.run_script("auto_target_logger.py", is_wordlist=True)
        else:
            self.wordlist_active = False
            self.wordlist_btn.config(text="📝 START WORDLIST", bg=self.btn_color)
            if self._wordlist_process: self._wordlist_process.terminate()

if __name__ == "__main__":
    app = FloatingController()
    app.root.mainloop()
