# utility.py
import sys
import subprocess

# Auto-install missing libraries
required_libs = [
    "selenium",
    "webdriver-manager",
    "tqdm",
    "google-generativeai",
    "Flask",
    "requests" 
]

def install_missing_libs():
    """Checks for and installs required Python libraries."""
    try:
        print("Checking/Updating pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    except Exception as e:
        print(f"⚠️ Could not update pip: {e}. Continuing with current version.")

    for lib in required_libs:
        try:
            if lib == "google-generativeai":
                __import__("google.generativeai")
            elif lib == "Flask":
                __import__("flask")
            else:
                __import__(lib.replace("-", "_"))
        except ImportError:
            print(f"📦 Installing missing library: {lib} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])