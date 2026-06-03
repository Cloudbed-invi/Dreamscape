import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk, ImageDraw
import os
import glob

class InteractiveMapper:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dreamscape - Professional Mapper")
        self.root.geometry("1150x850")
        self.root.configure(bg="#1e1e1e")

        # 1. Load Data
        self.targets = []
        if os.path.exists("targets.txt"):
            with open("targets.txt", "r") as f:
                self.targets = [line.strip() for line in f if line.strip()]
        
        self.master_dict = {}
        self.canvas_objects = {} 
        self.current_idx = 0

        # 2. Find Images
        self.map_files = glob.glob("maps/*.png")
        if not self.map_files:
            messagebox.showerror("Error", "No map images found in 'maps/' folder.")
            self.root.destroy()
            return
        
        self.img_path = self.map_files[0]
        
        # 3. UI Layout
        self.side_panel = tk.Frame(self.root, bg="#2a2a2a", width=280)
        self.side_panel.pack(side="right", fill="y", padx=5, pady=5)

        # Map Selector
        tk.Label(self.side_panel, text="SELECT MAP FILE", bg="#2a2a2a", fg="#888888", font=("Arial", 8)).pack(pady=(10,0))
        self.map_selector = ttk.Combobox(self.side_panel, values=[os.path.basename(f) for f in self.map_files], state="readonly")
        self.map_selector.pack(fill="x", padx=10, pady=5)
        self.map_selector.set(os.path.basename(self.img_path))
        self.map_selector.bind("<<ComboboxSelected>>", self.change_map)

        tk.Label(self.side_panel, text="ITEMS TO MAP", bg="#333333", fg="#00ff00", font=("Arial", 10, "bold")).pack(fill="x", pady=10)

        self.listbox = tk.Listbox(self.side_panel, bg="#1e1e1e", fg="white", font=("Arial", 10), selectbackground="#005500", relief="flat")
        self.listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.refresh_listbox()
        self.listbox.bind("<<ListboxSelect>>", self.on_list_select)

        # Buttons
        tk.Button(self.side_panel, text="RESET ITEM", command=self.reset_item, bg="#663333", fg="white", relief="flat").pack(fill="x", padx=10, pady=2)
        tk.Button(self.side_panel, text="SKIP ITEM", command=self.skip_item, bg="#444444", fg="white", relief="flat").pack(fill="x", padx=10, pady=2)
        tk.Button(self.side_panel, text="SAVE & EXPORT", command=self.save_dict, bg="#006600", fg="white", font=("Arial", 10, "bold"), relief="flat").pack(fill="x", padx=10, pady=10)

        self.canvas_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.canvas_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.canvas = tk.Canvas(self.canvas_frame, bg="black", cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Button-3>", self.on_right_click)

        self.load_image(self.img_path)
        self.update_selection()

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for t in self.targets:
            prefix = "● " if t in self.master_dict else "○ "
            self.listbox.insert(tk.END, f"{prefix}{t}")
            if t in self.master_dict:
                self.listbox.itemconfig(tk.END, fg="#00ff00")

    def load_image(self, path):
        self.img_path = path
        self.orig_img = Image.open(path)
        self.img_w, self.img_h = self.orig_img.size
        self.render_image()

    def change_map(self, event):
        new_file = self.map_selector.get()
        new_path = os.path.join("maps", new_file)
        self.load_image(new_path)
        self.master_dict = {} # Reset current mapping for new image
        self.canvas.delete("all")
        self.render_image()
        self.refresh_listbox()
        self.current_idx = 0
        self.update_selection()

    def render_image(self):
        self.canvas.delete("all")
        display_h = 780
        ratio = display_h / self.img_h
        display_w = int(self.img_w * ratio)
        self.display_ratio = ratio
        resized = self.orig_img.resize((display_w, display_h), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(resized)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

    def on_left_click(self, event):
        if self.current_idx >= len(self.targets): return
        item_name = self.targets[self.current_idx]
        self.clear_canvas_item(item_name)

        real_x = int(event.x / self.display_ratio)
        real_y = int(event.y / self.display_ratio)
        self.master_dict[item_name] = (real_x, real_y)
        
        ov = self.canvas.create_oval(event.x-5, event.y-5, event.x+5, event.y+5, fill="#00ff00", outline="white")
        tx = self.canvas.create_text(event.x, event.y-15, text=item_name, fill="#00ff00", font=("Arial", 8, "bold"))
        self.canvas_objects[item_name] = [ov, tx]

        self.listbox.delete(self.current_idx)
        self.listbox.insert(self.current_idx, f"● {item_name}")
        self.listbox.itemconfig(self.current_idx, fg="#00ff00")

        self.current_idx = (self.current_idx + 1) % len(self.targets)
        self.update_selection()

    def on_right_click(self, event):
        self.reset_item()

    def clear_canvas_item(self, item_name):
        if item_name in self.canvas_objects:
            for obj_id in self.canvas_objects[item_name]:
                self.canvas.delete(obj_id)
            del self.canvas_objects[item_name]

    def reset_item(self):
        if self.current_idx < len(self.targets):
            item_name = self.targets[self.current_idx]
            if item_name in self.master_dict: del self.master_dict[item_name]
            self.clear_canvas_item(item_name)
            self.listbox.delete(self.current_idx)
            self.listbox.insert(self.current_idx, f"○ {item_name}")
            self.listbox.itemconfig(self.current_idx, fg="white")
            self.update_selection()

    def on_list_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            self.current_idx = selection[0]
            self.update_selection()

    def update_selection(self):
        if self.current_idx < len(self.targets):
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_idx)
            self.listbox.see(self.current_idx)

    def skip_item(self):
        self.current_idx = (self.current_idx + 1) % len(self.targets)
        self.update_selection()

    def save_dict(self):
        if not self.master_dict:
            messagebox.showwarning("Warning", "No items mapped!")
            return
        
        # 1. Save Dict
        output = f"master_dict = {str(self.master_dict)}"
        with open("master_dict.txt", "w") as f:
            f.write(output)
        
        # 2. Export Reference Image
        preview_dir = os.path.join("archives", "mapped_previews")
        os.makedirs(preview_dir, exist_ok=True)
        
        # Draw on original high-res image
        draw_img = self.orig_img.copy()
        draw = ImageDraw.Draw(draw_img)
        for name, (x, y) in self.master_dict.items():
            draw.ellipse([x-10, y-10, x+10, y+10], fill=(0, 255, 0), outline=(255, 255, 255))
            draw.text((x, y-30), name, fill=(0, 255, 0))
        
        preview_path = os.path.join(preview_dir, f"mapped_{os.path.basename(self.img_path)}")
        draw_img.save(preview_path)
        
        messagebox.showinfo("Success", f"Saved {len(self.master_dict)} items!\nReference Image saved to archives/mapped_previews/")
        self.root.destroy()

if __name__ == "__main__":
    app = InteractiveMapper()
    app.root.mainloop()
