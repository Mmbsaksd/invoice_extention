import subprocess
import time
import sys
import os

def run():
    print("🚀 Starting SAP Automator Ecosystem...")
    
    # 1. Start API (FastAPI)
    print("📡 Starting API on port 8000...")
    api_proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.routes:app", "--port", "8000", "--reload"], 
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    # 2. Wait a bit for API
    time.sleep(2)

    # 3. Start Web App (Streamlit)
    print("🌐 Starting Web App on port 8501...")
    web_proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "web_app/app.py"], 
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    print("\n✅ System is READY!")
    print(" - API: http://localhost:8000")
    print(" - Web App: http://localhost:8501")
    print(" - Extension: Load the 'extension' folder in Chrome.")
    print("\nPress Ctrl+C to stop everything.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping System...")
        api_proc.terminate()
        web_proc.terminate()
        print("Done.")

if __name__ == "__main__":
    run()
