import ctypes
import ctypes.wintypes as wintypes

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def foreach_window(hwnd, lParam):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if "Player 1" in buf.value:
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            
            class_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_buf, 256)
            
            print(f"[{buf.value}] (Class: {class_buf.value}) Left: {rect.left}, Top: {rect.top}, Right: {rect.right}, Bottom: {rect.bottom}")
    return True

user32.EnumWindows(EnumWindowsProc(foreach_window), 0)
