"""
Start the Litmus API, reliably.

Exists because `pkill` does not kill Windows Python processes: a previous
uvicorn keeps port 8000, the new one fails to bind, and you spend twenty
minutes debugging "my changes aren't working" while a stale server serves old
code. This frees the port first, every time.

    python run_backend.py            # port 8000
    python run_backend.py --port 8010
"""
import argparse
import os
import subprocess
import sys
import time


def free_port(port: int) -> None:
    """Kill whatever currently holds the port."""
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return
    pids = {
        line.split()[-1]
        for line in out.splitlines()
        if f":{port} " in line and "LISTENING" in line
    }
    for pid in pids:
        print(f"  freeing port {port} — stopping stale PID {pid}")
        subprocess.run(["taskkill", "/F", "/PID", pid],
                       capture_output=True, text=True)
    if pids:
        time.sleep(2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    free_port(args.port)

    here = os.path.dirname(os.path.abspath(__file__))
    print(f"  starting Litmus API on {args.host}:{args.port}")
    os.chdir(os.path.join(here, "backend"))
    sys.exit(subprocess.call([
        sys.executable, "-m", "uvicorn", "app:app",
        "--host", args.host, "--port", str(args.port),
    ]))


if __name__ == "__main__":
    main()
