import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.window_manager import window_manager
from automation.screen_vision import screen_vision
import psutil

active = window_manager.get_active_window_title()
windows = [w['title'] for w in window_manager.get_open_windows()][:6]
apks = [f"{a['app_name']} ({a['filename']})" for a in screen_vision.find_all_apks()[:3]]
cpu = psutil.cpu_percent(interval=None)
ram = psutil.virtual_memory().percent

print('Active window:', repr(active))
print('Open windows:', windows)
print('Known APKs:', apks)
print(f'System: CPU {cpu}%, RAM {ram}%')
