import sys
import os

# Ensure the root directory is in the path for modular imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_app.app import main

if __name__ == "__main__":
    main()
