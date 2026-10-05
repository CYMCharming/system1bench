"""Admit existing/downloaded original weights only after upstream byte checks.

The local HF token is used only for authenticated metadata requests and is never
printed, serialized, put in subprocess arguments or copied between hosts.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import sha
from research.startlux_transfer_v1.run import save


def main():
    import fcntl
    import requests
    from huggingface_hub import get_token
    parser = argparse.ArgumentParser()
    for name in ('name', 'repo', 'revision', 'path', 'provenance'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    path = Path(args.path)
    token = get_token()
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    response = requests.get('https://huggingface.co/api/models/' + args.repo + '/revision/' + args.revision,
                            params={'blobs': 'true'}, headers=headers, timeout=60)
    if response.status_code != 200:
        raise RuntimeError('Upstream metadata HTTP ' + str(response.status_code))
    upstream = response.json()
    assert upstream['sha'] == args.revision
    cfg = json.loads((path / 'config.json').read_text())
    assert not cfg.get('quantization_config'), 'Quantization config rejected'
    names = {f['rfilename']: f for f in upstream['siblings']}
    weights = sorted(n for n in names if '/' not in n and n.endswith('.safetensors'))
    assert weights
    receipt = dict(model=args.name, repo=args.repo, revision=args.revision,
                   provenance=args.provenance, upstream_license=upstream.get('cardData', {}).get('license'),
                   quantization_config=False, verification='all weight SHA-256 against pinned upstream LFS',
                   weights={}, input_files={})
    for filename in weights:
        file = path / filename
        assert file.is_file(), 'Missing shard: ' + filename
        expected = names[filename]['lfs']['sha256']
        actual = sha(file)
        assert actual == expected, 'Altered weight: ' + filename
        with file.open('rb') as stream:
            length = struct.unpack('<Q', stream.read(8))[0]
            assert length < 100_000_000
            tensors = json.loads(stream.read(length))
        dtypes = Counter(t['dtype'] for n, t in tensors.items() if n != '__metadata__')
        assert set(dtypes) <= {'BF16', 'F16', 'F32', 'F64'}, 'Non-floating model tensor'
        receipt['weights'][filename] = dict(sha256=actual, bytes=file.stat().st_size, tensor_dtypes=dict(dtypes))
        print('WEIGHT_VERIFIED', args.name, filename, flush=True)
    # Verify config, complete tokenizer and chat template as upstream Git blobs.
    for filename in names:
        if '/' in filename or not filename.endswith(('.json', '.jinja', '.model', '.txt')):
            continue
        file = path / filename
        if not file.exists():
            if filename.startswith(('tokenizer', 'config', 'chat_template', 'vocab', 'merges', 'special_tokens', 'added_tokens', 'model.safetensors.index')):
                raise AssertionError('Missing input file: ' + filename)
            continue
        content = file.read_bytes()
        expected = names[filename].get('lfs', {}).get('sha256')
        if expected:
            assert hashlib.sha256(content).hexdigest() == expected, filename
        elif names[filename].get('blobId'):
            git_hash = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
            assert git_hash == names[filename]['blobId'], 'Altered input file: ' + filename
        else:
            raise AssertionError('Upstream input hash unavailable: ' + filename)
        receipt['input_files'][filename] = hashlib.sha256(content).hexdigest()
    out = Path(__file__).parent / 'admissions' / (args.name + '.json')
    save(out, receipt)
    pins_path = ROOT / '.aris/startlux_transfer_paths.json'
    with pins_path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        pins = json.loads(pins_path.read_text())
        pins[args.name] = dict(repo=args.repo, revision=args.revision, path=str(path.resolve()),
                               admission_sha256=sha(out), provenance=args.provenance)
        save(pins_path, pins)
    print('ADMITTED', args.name, flush=True)


if __name__ == '__main__':
    main()
