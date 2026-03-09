import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

def get_window_rect(window_name):
    hwnd = user32.FindWindowW(None, window_name)
    if hwnd:
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        print(f"[{window_name}] Left: {rect.left}, Top: {rect.top}, Right: {rect.right}, Bottom: {rect.bottom}")
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        
        # We want the bottom part, maybe bottom 1/4?
        # Let's say bottom 450 pixels (like ADB capture of roughly 450 out of 1600, which is ~28%)
        # Here we'll just take the bottom 30% of the window
        bottom_h = int(height * 0.30)
        bottom_top = rect.bottom - bottom_h
        
        print("\n--- MSS CAPTURE_REGION for Bottom UI ---")
        print(f"CAPTURE_REGION = {{\n    'top': {bottom_top},\n    'left': {rect.left},\n    'width': {width},\n    'height': {bottom_h}\n}}")
        
    else:
        print(f"Window '{window_name}' not found!")

get_window_rect("Player 1")
