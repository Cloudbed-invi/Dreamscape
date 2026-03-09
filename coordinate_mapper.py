# INSTRUCTIONS:
# 1. Create a folder named 'maps' in the same directory as this script.
# 2. Place your background screenshots (.png or .jpg) inside the 'maps' folder.
# 3. Run the script. Press 'n' to cycle through the images.

import cv2
import os
import glob

# Define the objects list
objects_list = [
    "pouch", "steak", "harpoon", "cat", "sea turtle", "hot air balloon", 
    "window", "fishing net", "potato", "oar", "oxygen tank", "fishing rod", 
    "z", "whale", "rudder", "seahorse", "signboard", "lighthouse", 
    "sailboat", "volleyball", "exhaust fan", "pumpkin", "parasol", 
    "backpack", "lifebuoy", "chimney", "drifting bottle", "jar", 
    "bench", "flag"
]

coordinates = {}
current_idx = 0
current_img_idx = 0
image_paths = []
current_img = None

def get_image_files(directory="maps"):
    """Fetch all .png and .jpg files from the specified directory."""
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        print("Please create it and add your images.")
        return []
    
    files = []
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]:
        files.extend(glob.glob(os.path.join(directory, ext)))
    
    if not files:
        print(f"Error: No image files found in '{directory}'.")
        
    return sorted(files)

def format_dict(d):
    """Formats a dictionary into a clean, copy-pasteable Python string."""
    lines = ["{"]
    for k, v in d.items():
        lines.append(f"    '{k}': {v},")
    lines.append("}")
    return "\n".join(lines)

def load_current_image():
    """Loads and standardizes the current image to exactly 900x1600."""
    global current_img, current_img_idx, image_paths
    
    if not image_paths:
        return False
        
    img_path = image_paths[current_img_idx]
    img = cv2.imread(img_path)
    
    if img is None:
        print(f"Error: Could not read image at {img_path}")
        return False
        
    # Standardize to 900x1600 (width, height) for memory coordinates
    current_img = cv2.resize(img, (900, 1600))
    return True

def refresh_window():
    global current_idx, current_img
    
    if current_idx >= len(objects_list) or current_img is None:
        return

    # Resize standardized image to exactly 450x800 for display
    display_img = cv2.resize(current_img.copy(), (450, 800))
    
    current_object = objects_list[current_idx]
    text = f"Mapping: {current_object} | Press 'n' to swap map"
    
    # Text settings for the overlay
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 1
    
    # Get text size to draw a background rectangle
    text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
    
    # Background rectangle coordinates at the top
    rect_x1 = 5
    rect_y1 = 5
    rect_x2 = rect_x1 + text_size[0] + 10
    rect_y2 = rect_y1 + text_size[1] + 10
    
    # Draw black rectangle (filled)
    cv2.rectangle(display_img, (rect_x1, rect_y1), (rect_x2, rect_y2), (0, 0, 0), cv2.FILLED)
    
    # Draw white text over the black rectangle
    text_x = rect_x1 + 5
    text_y = rect_y1 + text_size[1] + 5
    cv2.putText(display_img, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)
    
    cv2.imshow("Multi-Image Mapper (Scaled View)", display_img)

def mouse_callback(event, x, y, flags, param):
    global current_idx
    
    if current_idx >= len(objects_list):
        return
        
    current_object = objects_list[current_idx]
    
    if event == cv2.EVENT_LBUTTONDOWN:
        # Left click: Save coordinate against 900x1600 baseline and advance
        orig_x, orig_y = x * 2, y * 2
        coordinates[current_object] = (orig_x, orig_y)
        print(f"Mapped '{current_object}' to ({orig_x}, {orig_y})")
        current_idx += 1
        
        if current_idx < len(objects_list):
            refresh_window()
        else:
            print("\nFinished mapping all objects!")
            
    elif event == cv2.EVENT_RBUTTONDOWN:
        # Right click: Skip and advance
        print(f"Skipped '{current_object}'")
        current_idx += 1
        
        if current_idx < len(objects_list):
            refresh_window()
        else:
            print("\nFinished mapping all objects!")

def main():
    global current_idx, current_img_idx, image_paths
    
    # Load all image paths from the 'maps' directory
    image_paths = get_image_files("maps")
    if not image_paths:
        return

    # Load and standardize the first image
    if not load_current_image():
        return

    # Setup window and callback
    cv2.namedWindow("Multi-Image Mapper (Scaled View)", cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback("Multi-Image Mapper (Scaled View)", mouse_callback)

    # Initial draw of the first object to map
    refresh_window()

    # Main interaction loop
    while current_idx < len(objects_list):
        # Wait for 10ms
        key = cv2.waitKey(10) & 0xFF
        
        # Exit if ESC is pressed
        if key == 27:
            print("Operation cancelled by user (ESC).")
            break
            
        # Cycle images if 'n' or 'N' is pressed
        elif key == ord('n') or key == ord('N'):
            current_img_idx = (current_img_idx + 1) % len(image_paths)
            print(f"Swapped background map to: {os.path.basename(image_paths[current_img_idx])}")
            load_current_image()
            refresh_window()
        
        # Check if the window was closed manually using the 'X' button
        try:
            if cv2.getWindowProperty("Multi-Image Mapper (Scaled View)", cv2.WND_PROP_VISIBLE) < 1:
                print("Window closed manually.")
                break
        except Exception:
            break

    # Close OpenCV windows cleanly
    cv2.destroyAllWindows()

    if not coordinates:
        print("\nNo coordinates mapped. Exiting without saving.")
        return

    # Get formatted dictionary string
    dict_str = format_dict(coordinates)
    
    # Print the fully populated Python dictionary to the terminal
    print("\n--- Final Coordinates Dictionary (900x1600 Baseline) ---")
    print(dict_str)

    # Save to a text file
    output_file = "master_dict.txt"
    try:
        with open(output_file, "w") as f:
            f.write(dict_str + "\n")
        print(f"\nCoordinates successfully saved to {output_file}")
    except Exception as e:
        print(f"\nError saving to file: {e}")

if __name__ == "__main__":
    main()
