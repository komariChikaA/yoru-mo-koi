"""Open the persistent local brow pen editor without a terminal window."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8769'


def ready():
    try:
        with urllib.request.urlopen(URL+'/api/state', timeout=1) as response:
            return json.load(response).get('app') == 'brow-pen'
    except (OSError, ValueError):
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    if not ready():
        folder = ROOT/'output/brow-pen'
        folder.mkdir(parents=True, exist_ok=True)
        with (folder/'server.log').open('w', encoding='utf-8') as out, (folder/'server-errors.log').open('w', encoding='utf-8') as err:
            subprocess.Popen([sys.executable, '-X', 'utf8', str(ROOT/'tools/brow-pen/server.py')], cwd=ROOT,
                             stdout=out, stderr=err, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        for _ in range(40):
            if ready():
                break
            time.sleep(.2)
        else:
            raise SystemExit('编辑器启动失败，查看 output/brow-pen/server-errors.log')
    if not args.no_open:
        webbrowser.open(URL)
    print(URL)
