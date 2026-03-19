#!/usr/bin/env python
"""
Start ngrok tunnel to expose localhost:8000 publicly.

This script uses pyngrok to create a tunnel for ElevenLabs webhook callbacks.

Usage:
    python start_ngrok.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pyngrok import ngrok

if __name__ == "__main__":
    print("🚀 Starting ngrok tunnel...\n")
    
    try:
        # Set authtoken
        ngrok.set_auth_token("3B8u8PrTmybHVcb0ia1MkUdBz5Z_664rowHgr3wfggXLEg5yy")
        
        # Open a ngrok tunnel to port 8000
        public_url = ngrok.connect(8000, "http")
        print(f"✅ ngrok tunnel is live!")
        print(f"\n📍 Public URL: {public_url}")
        print(f"\n⚙️  Update your ElevenLabs agent webhook to:")
        print(f"   {public_url}/webhook/elevenlabs\n")
        print("Press CTRL+C to close the tunnel.\n")
        
        # Keep the tunnel open
        ngrok_process = ngrok.get_ngrok_process()
        ngrok_process.proc.wait()
        
    except KeyboardInterrupt:
        print("\n\n👋 Closing ngrok tunnel...")
        ngrok.kill()
        print("✓ Tunnel closed")
    except Exception as e:
        print(f"❌ Error starting ngrok: {e}")
        sys.exit(1)
