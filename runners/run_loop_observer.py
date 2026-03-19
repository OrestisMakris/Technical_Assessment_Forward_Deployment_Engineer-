#!/usr/bin/env python3
"""
Run the refinement loop with live observation UI.

The UI will be available at:
  http://localhost:8000/

Steps:
1. This script starts the FastAPI backend
2. Open the UI in your browser
3. Click "RUN AGAIN" to start the loop
4. Watch the live feed of conversation, scores, and iteration history
"""

import subprocess
import webbrowser
import time
import sys
import os

def main():
    print("=" * 80)
    print("🔄 TECHMELLON AIRLINES - LOOP OBSERVER")
    print("=" * 80)
    print()
    
    # Check if in the right directory
    if not os.path.exists("backend"):
        print("❌ Error: backend/ directory not found")
        print("Run this script from the project root")
        sys.exit(1)
    
    print("📡 Starting FastAPI backend...")
    print()
    
    try:
        # Start the backend
        cmd = [
            sys.executable, 
            "-m", "uvicorn",
            "backend.main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--reload"
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        print(f"✅ Backend starting on http://localhost:8000")
        print()
        
        # Wait for server to start
        time.sleep(3)
        
        # Open the UI
        print("🌐 Opening Loop Observer UI...")
        webbrowser.open("http://localhost:8000/")
        
        print()
        print("=" * 80)
        print("UI Instructions:")
        print("=" * 80)
        print("1. The Loop Observer UI is now open in your browser")
        print("2. Click the '▶️ RUN AGAIN' button to start the refinement loop")
        print("3. Watch live:")
        print("   - Conversation feed (left panel)")
        print("   - Current iteration scores (right panel)")
        print("   - Iteration history (bottom left)")
        print("   - Prompt changes as diffs (bottom right)")
        print()
        print("The loop will run up to 5 iterations or until all tests pass.")
        print("No manual intervention needed - just observe!")
        print()
        print("Press Ctrl+C to stop the backend")
        print("=" * 80)
        print()
        
        # Keep the process running
        process.wait()
    
    except KeyboardInterrupt:
        print("\n\n✋ Stopping backend...")
        process.terminate()
        process.wait()
        print("✅ Backend stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
