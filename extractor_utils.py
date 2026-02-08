import os
import json
from pathlib import Path

CONFIG_FILE = "extractor_config.json"

def load_config():
    """Load saved extractor paths from config file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_config(config):
    """Save extractor paths to config file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except:
        return False

def find_winrar_path():
    """Find WinRAR in common paths only"""
    common_paths = [
        r"C:\Program Files\WinRAR\WinRAR.exe",  # Most common location
        r"C:\Program Files (x86)\WinRAR\WinRAR.exe",
        r"C:\WinRAR\WinRAR.exe"
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None

def get_available_extractors():
    """Get available extraction tools from config and common paths"""
    config = load_config()
    tools = []
    
    # Check saved WinRAR path first
    if config.get("winrar") and os.path.exists(config["winrar"]):
        tools.append(("winrar", config["winrar"]))
    else:
        # Check common paths
        winrar = find_winrar_path()
        if winrar:
            tools.append(("winrar", winrar))
    
    return tools

def set_tool_path(tool_name, path):
    """Save tool path to config"""
    config = load_config()
    config[tool_name] = path
    save_config(config)

def get_common_paths():
    """Get common installation paths for user selection"""
    return {
        "WinRAR": [
            r"C:\Program Files\WinRAR\WinRAR.exe",
            r"C:\Program Files (x86)\WinRAR\WinRAR.exe",
            r"C:\WinRAR\WinRAR.exe"
        ]
    }
