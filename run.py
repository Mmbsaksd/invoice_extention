import subprocess
import time
import sys
import os

def run():
    print("Starting Simplified Invoice Assistant...")
    
    # Start API using the new root api.py
    api_proc = subprocess.Popen(
        [sys.executable, "api.py"], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True
    )

    print("\nAPI: http://localhost:8000")
    print("Extension: Load the 'extension' folder in Chrome.")
    print("\nPress Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        api_proc.terminate()

if __name__ == "__main__":
    run()
