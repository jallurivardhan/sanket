import subprocess
import sys
import os
import time

def check_docker():
    try:
        subprocess.run(
          ["docker", "--version"], 
          capture_output=True, check=True)
        return True
    except:
        return False

def run_local():
    """Run backend and frontend locally without Docker"""
    print("Starting Sanket locally...")
    print("Make sure Redis is running on port 6379")
    print()
    
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn",
         "backend.api.main:app",
         "--host", "0.0.0.0",
         "--port", "8000",
         "--reload"],
        cwd=os.path.dirname(
          os.path.abspath(__file__))
    )
    
    print("Backend starting on http://localhost:8000")
    print("Health check: http://localhost:8000/health")
    print("API docs: http://localhost:8000/docs")
    print()
    print("To start frontend:")
    print("  cd frontend && npm run dev")
    print()
    print("Press Ctrl+C to stop")
    
    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        print("Shutting down...")
        backend_proc.terminate()

if __name__ == "__main__":
    run_local()
