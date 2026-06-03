import ctypes
from ctypes import wintypes
from pathlib import Path
import mss
import mss.tools

# Force DPI awareness so pixels perfectly match screen
ctypes.windll.user32.SetProcessDPIAware()
user32 = ctypes.windll.user32

def get_client_rect(window_name):
    hwnd = user32.FindWindowW(None, window_name)
    if not hwnd:
        print(f"Window '{window_name}' not found!")
        return None

    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    
    point = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    
    # Raw client area
    c_left = point.x
    c_top = point.y
    c_width = rect.right
    c_height = rect.bottom
    
    # Calculate aspect ratio of current client area
    aspect_ratio = c_width / c_height
    target_aspect = 900 / 1600 # 0.5625
    
    print(f"[{window_name} Raw Inner] Left: {c_left}, Top: {c_top}, Width: {c_width}, Height: {c_height}, Aspect: {aspect_ratio:.2f}")
    
    # If the window is wider than 900:1600, it has black bars on the sides
    if aspect_ratio > target_aspect:
        # Calculate true game width based on height
        true_width = int(c_height * target_aspect)
        # Shift left by half the black bar size to center on the game
        c_left = c_left + int((c_width - true_width) / 2)
        c_width = true_width
        print(f"-> Strip Sidebars: New Left {c_left}, New Width {c_width}")
    
    # Bottom 30% calculation of the TRUE game area
    bottom_h = int(c_height * 0.30)
    bottom_top = (c_top + c_height) - bottom_h
    
    capture_dict = {
        'top': bottom_top,
        'left': c_left,
        'width': c_width,
        'height': bottom_h
    }
    
    print("\n--- NEW PRECISE MSS CAPTURE_REGION ---")
    print(f"CAPTURE_REGION = {{\n    'top': {capture_dict['top']},\n    'left': {capture_dict['left']},\n    'width': {capture_dict['width']},\n    'height': {capture_dict['height']}\n}}")
    
    return capture_dict

capture_region = get_client_rect("Player 1")

if capture_region:
    print(f"\nTaking test screenshot of region: {capture_region}...")
    with mss.mss() as sct:
        sct_img = sct.grab(capture_region)
        output_path = Path("mss_region_debug.png")
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(output_path))
        print(f"Success! Saved precise test screenshot to: {output_path.absolute()}")
