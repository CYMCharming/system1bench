"""Read-only status for the four one-off shards; never reports partial scores."""
import json
from pathlib import Path
import shlex
import subprocess

from research.evaluation_completion_v3.run import HERE, PRIVATE, read


def main():
    manifest = read(HERE / 'manifest.json')
    processes = subprocess.check_output(['ps', '-eo', 'args'], text=True).splitlines()
    workers = []
    for command in processes:
        try:
            args = shlex.split(command)
        except ValueError:
            continue
        if len(args) > 1 and Path(args[0]).name.startswith('python') and args[1].endswith('research/evaluation_completion_v3/run.py'):
            workers.append(args)
    cells = []
    for model, plan in manifest['plans'].items():
        for part in plan['shards']:
            folder = PRIVATE / 'shards' / model / str(part['part']) / 'intent' / model
            active = any('--model' in args and args[args.index('--model') + 1] == model and
                         '--part' in args and args[args.index('--part') + 1] == str(part['part'])
                         for args in workers)
            complete = (folder / 'DONE.json').exists()
            status = read(folder / ('DONE.json' if complete else 'status.json')) if (
                complete or (folder / 'status.json').exists()) else {}
            n = status.get('n', status.get('completed', 0))
            assert n <= part['expected']
            if complete:
                assert n == part['expected']
            cells.append(dict(model=model, part=part['part'], completed=n, expected=part['expected'],
                              done=complete, active=active, errors=status.get('errors', 0)))
    print(json.dumps(dict(cells=cells, all_done=all(c['done'] for c in cells),
                          needs_attention=any(c['errors'] or (not c['done'] and not c['active']) for c in cells))))


if __name__ == '__main__':
    main()
