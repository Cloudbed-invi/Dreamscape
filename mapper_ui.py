import tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageTk
import json
import os

class PostRoundMapper:
    def __init__(self, profile_path, baseline_image_path, unknown_words, adb_w, adb_h, on_complete, master=None):
        self.profile_path = profile_path
        self.baseline_image_path = baseline_image_path
        # Sort unknowns by length descending so long words are at the top and 3/4 letter junk words sink to the bottom
        self.unknown_words = sorted([u for u in unknown_words if u], key=len, reverse=True)
        self.adb_w = adb_w
        self.adb_h = adb_h
        self.on_complete = on_complete
        
        with open(self.profile_path, 'r') as f:
            self.profile_data = json.load(f)
            
        if master:
            self.root = tk.Toplevel(master)
            self.root.attributes("-alpha", 1.0)
            self.root.attributes("-transparentcolor", "")
            self.root.overrideredirect(False)
            self.is_toplevel = True
        else:
            self.root = tk.Tk()
            self.is_toplevel = False
            
        self.root.title("Map Unknown Items")
        self.root.geometry("1000x800")
        
        # Force window to the absolute front!
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(500, lambda: self.root.attributes('-topmost', False))
        self.root.focus_force()
        
        self.setup_ui()
        if not self.is_toplevel:
            self.root.mainloop()
        else:
            self.root.wait_window()
            
    def setup_ui(self):
        # Left Panel for Words
        self.left_frame = tk.Frame(self.root, width=320, bg="#2b2b2b")
        self.left_frame.pack(side="left", fill="y")
        self.left_frame.pack_propagate(False)
        
        # Bottom Buttons
        tk.Button(self.left_frame, text="Finish & Resume Bot", bg="#2196F3", fg="white", font=("Arial", 12, "bold"), command=self.finish).pack(side="bottom", pady=15, fill="x", padx=10)
        tk.Button(self.left_frame, text="Add Custom Target", bg="#9C27B0", fg="white", font=("Arial", 12, "bold"), command=self.add_custom_target).pack(side="bottom", pady=5, fill="x", padx=10)
        
        # Scrollable Canvas setup
        self.scroll_canvas = tk.Canvas(self.left_frame, bg="#2b2b2b", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.left_frame, orient="vertical", command=self.scroll_canvas.yview)
        
        self.scroll_frame = tk.Frame(self.scroll_canvas, bg="#2b2b2b")
        self.scroll_frame.bind("<Configure>", lambda e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))
        
        self.scroll_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=300)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.word_frames = {}
        
        # Right Panel for Image
        self.right_frame = tk.Frame(self.root)
        self.right_frame.pack(side="right", fill="both", expand=True)
        
        self.canvas = tk.Canvas(self.right_frame, bg="black")
        self.canvas.pack(fill="both", expand=True)
        
        # Load and scale image
        self.img_orig = Image.open(self.baseline_image_path)
        
        # We need to fit it in the canvas. Let's force an update to get canvas size.
        self.root.update()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        
        # Scale preserving aspect ratio
        img_ratio = self.img_orig.width / self.img_orig.height
        canvas_ratio = cw / ch
        
        if img_ratio > canvas_ratio:
            new_w = cw
            new_h = int(cw / img_ratio)
        else:
            new_h = ch
            new_w = int(ch * img_ratio)
            
        self.display_img = self.img_orig.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.display_img)
        
        # Calculate scaling factors for recording coordinates
        self.scale_x = self.img_orig.width / new_w
        self.scale_y = self.img_orig.height / new_h
        
        self.image_id = self.canvas.create_image(cw//2, ch//2, image=self.photo, anchor="center")
        
        # Mapping State
        self.current_mapping_word = None
        self.current_orig_word = None
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
        self.instruction_label = tk.Label(self.right_frame, text="Click 'MAP' on a word to begin.", bg="black", fg="yellow", font=("Arial", 12))
        self.instruction_label.pack(side="bottom", fill="x")
        
        self.refresh_left_panel()
        
        # Draw initially
        self.root.update()
        self.draw_mapped_targets()
        
    def refresh_left_panel(self):
        # Clear existing
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.word_frames.clear()
        
        # Unmapped Targets
        tk.Label(self.scroll_frame, text="Unmapped Items", fg="#FFC107", bg="#2b2b2b", font=("Arial", 14, "bold")).pack(pady=(10, 5))
        
        if not self.unknown_words:
            tk.Label(self.scroll_frame, text="No unmapped items.", fg="white", bg="#2b2b2b").pack(pady=5)
            
        for word in self.unknown_words:
            frame = tk.Frame(self.scroll_frame, bg="#3b3b3b", pady=5)
            frame.pack(fill="x", padx=10, pady=2)
            
            var = tk.StringVar(value=word)
            ent = tk.Entry(frame, textvariable=var, fg="black", bg="white", font=("Arial", 11), width=15)
            ent.pack(side="left", padx=5)
            
            btn_map = tk.Button(frame, text="MAP", bg="#4CAF50", fg="white", command=lambda w=word, v=var: self.start_mapping(w, v))
            btn_map.pack(side="left", padx=2)
            
            btn_junk = tk.Button(frame, text="JUNK", bg="#f44336", fg="white", command=lambda w=word: self.mark_junk(w))
            btn_junk.pack(side="left", padx=2)
            
            self.word_frames[word] = frame

        # Mapped Targets
        tk.Label(self.scroll_frame, text="Currently Mapped", fg="#4CAF50", bg="#2b2b2b", font=("Arial", 14, "bold")).pack(pady=(15, 5))
        mapped = self.profile_data.get("targets", [])
        
        if not mapped:
            tk.Label(self.scroll_frame, text="No items mapped yet.", fg="white", bg="#2b2b2b").pack(pady=5)
            
        for word in sorted(mapped):
            frame = tk.Frame(self.scroll_frame, bg="#3b3b3b", pady=5)
            frame.pack(fill="x", padx=10, pady=2)
            
            tk.Label(frame, text=word, fg="white", bg="#3b3b3b", font=("Arial", 11)).pack(side="left", padx=5, fill="x", expand=True, anchor="w")
            
            btn_unmap = tk.Button(frame, text="UNMAP", bg="#FF9800", fg="white", command=lambda w=word: self.unmap_target(w))
            btn_unmap.pack(side="right", padx=5)
            
    def draw_mapped_targets(self):
        self.canvas.delete("marker")
        bbox = self.canvas.bbox(self.image_id)
        if not bbox: return
        
        for word, coords in self.profile_data.get("coordinates", {}).items():
            pct_x, pct_y = coords
            orig_x = pct_x * self.img_orig.width
            orig_y = pct_y * self.img_orig.height
            
            rel_x = orig_x / self.scale_x
            rel_y = orig_y / self.scale_y
            
            canvas_x = rel_x + bbox[0]
            canvas_y = rel_y + bbox[1]
            
            self.canvas.create_oval(canvas_x-8, canvas_y-8, canvas_x+8, canvas_y+8, fill="green", outline="white", tags="marker")
            self.canvas.create_text(canvas_x, canvas_y-15, text=word, fill="white", font=("Arial", 10, "bold"), tags="marker")

    def unmap_target(self, word):
        if word in self.profile_data.get("targets", []):
            self.profile_data["targets"].remove(word)
        if word in self.profile_data.get("coordinates", {}):
            del self.profile_data["coordinates"][word]
            
        if word not in self.unknown_words:
            self.unknown_words.insert(0, word)
            
        self.refresh_left_panel()
        self.draw_mapped_targets()
        
    def add_custom_target(self):
        new_word = simpledialog.askstring("Add Target", "Enter exact name of the item to map:", parent=self.root)
        if new_word:
            new_word = " ".join([p.capitalize() for p in new_word.strip().split()])
            if new_word not in self.unknown_words and new_word not in self.profile_data.get("targets", []):
                self.unknown_words.insert(0, new_word)
                self.refresh_left_panel()

    def start_mapping(self, orig_word, string_var):
        actual_word = string_var.get().strip().title()
        if not actual_word: return
        self.current_orig_word = orig_word
        self.current_mapping_word = actual_word
        self.instruction_label.config(text=f"Click on the image to map: {actual_word}")
        
    def mark_junk(self, word):
        if word in self.unknown_words:
            self.unknown_words.remove(word)
            
        if self.current_orig_word == word:
            self.current_mapping_word = None
            self.current_orig_word = None
            self.instruction_label.config(text="Click 'MAP' on a word to begin.")
            
        self.refresh_left_panel()
        
    def on_canvas_click(self, event):
        if not self.current_mapping_word:
            return
            
        # Get image bounding box on canvas
        bbox = self.canvas.bbox(self.image_id)
        if not bbox: return
        img_x, img_y = bbox[0], bbox[1]
        
        # Relative click inside the scaled image
        rel_x = event.x - img_x
        rel_y = event.y - img_y
        
        # Ensure click is inside the image
        if rel_x < 0 or rel_y < 0 or rel_x > self.display_img.width or rel_y > self.display_img.height:
            return
            
        # Original screenshot pixel coordinates
        orig_x = int(rel_x * self.scale_x)
        orig_y = int(rel_y * self.scale_y)
        
        # Convert to percentages for the profile
        pct_x = round(orig_x / self.img_orig.width, 4)
        pct_y = round(orig_y / self.img_orig.height, 4)
        
        # Save to profile data
        if "coordinates" not in self.profile_data:
            self.profile_data["coordinates"] = {}
        if "targets" not in self.profile_data:
            self.profile_data["targets"] = []
            
        self.profile_data["coordinates"][self.current_mapping_word] = [pct_x, pct_y]
        if self.current_mapping_word not in self.profile_data["targets"]:
            self.profile_data["targets"].append(self.current_mapping_word)
            
        self.mark_junk(self.current_orig_word)
        self.draw_mapped_targets()
        
    def finish(self):
        # Save profile
        with open(self.profile_path, 'w') as f:
            json.dump(self.profile_data, f, indent=4)
            
        # Save baseline image to profiles folder for Launcher preview
        import shutil
        img_dest = os.path.splitext(self.profile_path)[0] + ".png"
        try:
            shutil.copy(self.baseline_image_path, img_dest)
        except Exception:
            pass
            
        print(f"Updated profile saved to {self.profile_path}")
        self.root.destroy()
        if self.on_complete:
            self.on_complete(self.profile_data.get("coordinates", {}))
