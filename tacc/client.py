"""Wait for the local Qwen service, then run client.sh. Started by service_supervisor.py with the
node's system Python (3.6+), so it uses the standard library only."""
import os
import subprocess
import sys
import time
import urllib.request

base = os.environ["QWEN_BASE_URL"]
wait_s = int(os.environ.get("SERVICE_WAIT_S", "1800"))
started = time.monotonic()
while True:
    try:
        with urllib.request.urlopen(base + "/models", timeout=5) as response:
            if response.status == 200:
                break
    except OSError:
        pass
    if time.monotonic() - started > wait_s:
        sys.exit("Qwen service did not become ready within {}s".format(wait_s))
    time.sleep(5)
print("SERVICE_READY after {:.0f}s".format(time.monotonic() - started), flush=True)
sys.exit(subprocess.call(["bash", os.path.join(os.environ["TACC_WORKDIR"], "client.sh")]))
