import uvicorn
import os
import sys

# Ensure current working directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))
RELOAD = os.environ.get("RELOAD", "false").lower() in ("true", "1")

if __name__ == "__main__":
    print("==================================================================")
    print(" CineSeat — Cinema Seating & Showtimes Intelligence Engine API   ")
    print("==================================================================")
    print(f" API Server   : http://{HOST}:{PORT}")
    print(f" Scalar Docs  : http://{HOST}:{PORT}/docs (or /scalar)")
    print(f" Health Check : http://{HOST}:{PORT}/health")
    print("==================================================================")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=RELOAD)
