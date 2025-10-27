import sys
import subprocess

# Define required libraries with their corresponding import names
required_libs = {
    "selenium": "selenium",
    "webdriver-manager": "webdriver_manager",
    "tqdm": "tqdm",
    "Flask": "flask",
    "requests": "requests",
    "pyperclip": "pyperclip"
}

def install_missing_libs():
    """
    Checks for and installs required Python libraries using a robust mapping.
    """
    try:
        print("Checking/Updating pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    except Exception as e:
        print(f"⚠️ Could not update pip: {e}. Continuing with current version.")

    for pip_name, import_name in required_libs.items():
        try:
            # Try to import the library using its actual import name
            __import__(import_name)
            print(f"✅ {pip_name} is already installed.")
        except ImportError:
            # If the import fails, install it using its pip name
            print(f"📦 Installing missing library: {pip_name} ...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            except subprocess.CalledProcessError as e:
                print(f"❌ FAILED to install {pip_name}. Please install it manually: pip install {pip_name}")
                print(f"   Error: {e}")
                sys.exit(1) # Exit if a critical dependency fails to install