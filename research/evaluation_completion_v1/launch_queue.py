"""Sequential isolated workers; never terminates other GPU processes."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
TRANSFER_MISSING = {'english', 'multilingual', 'llama31_8b_instruct', 'nanojev'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', nargs='+', required=True)
    parser.add_argument('--after-pid', type=int)
    args = parser.parse_args()
    if args.after_pid:
        while True:
            try:
                os.kill(args.after_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(20)
    failures = []
    for model in args.models:
        for panel in ['intent', *(['transfer'] if model in TRANSFER_MISSING else [])]:
            result = subprocess.run([sys.executable, str(HERE / 'run.py'), '--models', model,
                                     '--panel', panel, '--worker'], check=False)
            if result.returncode:
                failures.append((model, panel, result.returncode))
    print('QUEUE FINISHED; failed cells:', failures, flush=True)


if __name__ == '__main__':
    main()
