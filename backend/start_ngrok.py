import os
import re
import time
from pyngrok import ngrok
from dotenv import load_dotenv

load_dotenv()
auth_token = os.getenv("NGROK_AUTHTOKEN")
if auth_token:
    ngrok.set_auth_token(auth_token)

def start_tunnel():
    try:
        from pyngrok import conf
        conf.get_default().region = "in"  # Connect to Asia/India region for stability
        tunnel = ngrok.connect(8000, bind_tls=True)
        public_url = tunnel.public_url.replace("http://", "https://")
        print(f"Ngrok URL (Region: IN): {public_url}", flush=True)

        # Update .env
        env_path = ".env"
        with open(env_path, "r") as f:
            content = f.read()

        content = re.sub(r"PUBLIC_BASE_URL=.*", f"PUBLIC_BASE_URL={public_url}", content)

        with open(env_path, "w") as f:
            f.write(content)

        print(".env updated successfully. Keeping tunnel alive...", flush=True)
        
        # Keep alive and monitor
        ngrok_process = ngrok.get_ngrok_process()
        try:
            ngrok_process.proc.wait()
        except KeyboardInterrupt:
            print("Shutting down ngrok.")
            ngrok.kill()
            return False
    except Exception as e:
        print(f"Ngrok crashed: {e}. Restarting...")
        ngrok.kill()
        return True
    return True

while start_tunnel():
    time.sleep(2)
