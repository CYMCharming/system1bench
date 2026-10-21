"""CPU-only, text-free reference-token lengths for frozen option descriptions.

No model weights, model inference, chat template, candidate ID, or state text
is used. Tokenizer files must already exist and match the immutable benchmark
admission receipts. Candidate text never enters the public artifact.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SPECS = {
    'qwen3': dict(
        repo='Qwen/Qwen3-8B',
        revision='b968826d9c46dd6066d109eabc6255188de91218',
        admission='research/model_expansion_v3/admissions/qwen3_8b.json',
        files=['config.json', 'tokenizer.json', 'tokenizer_config.json',
               'vocab.json', 'merges.txt'],
        label='Qwen3-8B reference tokenizer',
        provenance='Official Qwen repository; immutable, previously admitted cache.',
    ),
    'llama32': dict(
        repo='unsloth/Llama-3.2-3B-Instruct',
        revision='006f5dcd1393c3add266de40994ba96225e9689d',
        admission='research/model_expansion_v3/admissions/llama32_3b_public.json',
        files=['config.json', 'tokenizer.json', 'tokenizer_config.json',
               'special_tokens_map.json', 'chat_template.jinja'],
        label='Llama-3.2 reference tokenizer (Unsloth distribution)',
        provenance=('Pinned third-party Unsloth distribution; sensitivity reference only. '
                    'Tokenizer identity with the gated Meta distribution is not asserted.'),
    ),
}


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def sha(path: Path, *, text_lf=False) -> str:
    data = path.read_bytes()
    if text_lf:
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def digest(value) -> str:
    return hashlib.sha256(compact(value)).hexdigest()


def descriptions(root: Path, observations, *, main_path=None, transfer_path=None):
    """Recover exact private descriptions through frozen request SHA + qid."""
    questions = {}
    frozen_sources = {}
    for panel, override in [('main', main_path), ('transfer', transfer_path)]:
        spec = observations['frozen_sources'][panel]
        path = Path(override) if override else root / spec['canonical_path']
        if not path.exists() and override is None:
            path = root / '.aris/option_length_v1' / (panel + '.frozen.json')
        if sha(path) != spec['sha256']:
            raise ValueError('Frozen source hash mismatch: ' + panel)
        frozen_sources[panel] = dict(canonical_path=spec['canonical_path'], sha256=spec['sha256'])
        for suite in read(path)['suites']:
            for case in suite['cases']:
                request_sha = digest(dict(state=case['state'], questions=case['questions']))
                if request_sha != case['request_sha256']:
                    raise ValueError('Frozen request SHA mismatch')
                for qid, question in case['questions'].items():
                    if question['type'] != 'choice':
                        continue
                    key = request_sha, qid
                    existing = questions.setdefault(key, question)
                    if compact(existing) != compact(question):
                        raise ValueError('Conflicting question for identical request SHA')
    texts = {}
    for item in observations['items']:
        question = questions[item['request_sha256'], item['qid']]
        criteria = question['criteria']
        if list(criteria) != item['labels']:
            raise ValueError('Ordered candidate labels mismatch')
        candidates = list(criteria.values())
        hashes = [hashlib.sha256(text.encode('utf-8')).hexdigest() for text in candidates]
        if hashes != item['candidate_hashes']:
            raise ValueError('Exact candidate description SHA mismatch')
        lengths = [sum(not ch.isspace() for ch in text) for text in candidates]
        words = [len(text.split()) for text in candidates]
        if lengths != item['lengths'] or words != item['word_lengths']:
            raise ValueError('Character/word projection no longer matches exact text')
        for candidate_sha, text in zip(hashes, candidates):
            previous = texts.setdefault(candidate_sha, text)
            if previous != text:
                raise ValueError('Candidate SHA collision')
    expected = {h for item in observations['items'] for h in item['candidate_hashes']}
    if set(texts) != expected or len(texts) != 893:
        raise ValueError('Incomplete or changed candidate population')
    return texts, frozen_sources


def tokenizer_receipt(root: Path, name: str, folder: Path):
    """Admit only already-cached tokenizer bytes matching public source pins."""
    import tokenizers
    import transformers
    from transformers import AutoTokenizer

    spec = SPECS[name]
    admission_path = root / spec['admission']
    admission = read(admission_path)
    if admission['repo'] != spec['repo'] or admission['revision'] != spec['revision']:
        raise ValueError('Tokenizer repository/revision pin mismatch: ' + name)
    files = {}
    for filename in spec['files']:
        path = folder / filename
        # An optional external chat template is not consulted by encode().
        # Retain its identity when it is present in the admitted distribution.
        if filename == 'chat_template.jinja' and not path.exists():
            continue
        actual = sha(path)
        if actual != admission['input_files'][filename]:
            raise ValueError('Tokenizer file hash mismatch: ' + name + '/' + filename)
        files[filename] = actual
    tokenizer = AutoTokenizer.from_pretrained(folder, use_fast=True,
                                               local_files_only=True, trust_remote_code=False)
    if not tokenizer.is_fast:
        raise ValueError('A fast tokenizer is required for this frozen projection')
    receipt = dict(
        repo=spec['repo'], revision=spec['revision'], label=spec['label'],
        provenance=spec['provenance'], files=files,
        admission_source=spec['admission'], admission_sha256=sha(admission_path, text_lf=True),
        implementation=dict(python=platform.python_version(), transformers=transformers.__version__,
                            tokenizers=tokenizers.__version__, tokenizer_class=type(tokenizer).__name__,
                            use_fast=True, trust_remote_code=False, local_files_only=True),
        add_special_tokens=False, truncation=False, padding=False,
        encoding='tokenizer.encode(exact_candidate_description, add_special_tokens=False, truncation=False)',
        reference_only=True, native_model_tokens=False,
        scope='Standalone exact candidate description; no candidate ID, state, question instructions, chat template, or added leading separator.',
        caveat=('A common reference token count, not Jev or every compared model\'s native token count. '
                'Context-dependent tokenization of a full concatenated prompt can differ.'),
    )
    return tokenizer, receipt


def collect(root: Path, observations_path: Path, tokenizer_paths: dict,
            *, main_path=None, transfer_path=None):
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false')
    observations = json.loads(gzip.decompress(observations_path.read_bytes()))
    if observations['protocol'] != 'option-length-observations-v1' or len(observations['items']) != 2310:
        raise ValueError('Unexpected source observations')
    texts, frozen_sources = descriptions(root, observations, main_path=main_path, transfer_path=transfer_path)
    lengths = {candidate_sha: {} for candidate_sha in sorted(texts)}
    tokenizers = {}
    for name, folder in tokenizer_paths.items():
        tokenizer, receipt = tokenizer_receipt(root, name, folder)
        for candidate_sha in lengths:
            ids = tokenizer.encode(texts[candidate_sha], add_special_tokens=False, truncation=False)
            if not ids or not all(isinstance(value, int) for value in ids):
                raise ValueError('Invalid tokenization result')
            lengths[candidate_sha][name] = len(ids)
        tokenizers[name] = receipt
    if 'qwen3' not in tokenizers:
        raise ValueError('The primary Qwen3 reference is required')
    if any(set(cell) != set(tokenizers) for cell in lengths.values()):
        raise ValueError('Incomplete tokenizer coverage')
    output = dict(version=1, protocol='option-length-reference-tokens-v1',
                  source_observations_sha256=sha(observations_path),
                  primary_tokenizer='qwen3', candidate_count=len(texts), item_count=2310,
                  tokenizers=tokenizers, lengths=lengths,
                  text_included=False, model_weights_used=False, new_inference=False)
    if re.search(r'hf_[A-Za-z0-9]{25,}|apikey_[A-Za-z0-9_]+', compact(output).decode('utf-8')):
        raise ValueError('Credential-like string in public projection')
    bindings = dict(version=1, protocol=output['protocol'],
                    collector_sha256=sha(Path(__file__), text_lf=True),
                    source_observations=dict(path='research/option_length_v1/observations.json.gz',
                                             sha256=sha(observations_path)),
                    frozen_sources=frozen_sources, tokenizers=tokenizers,
                    candidate_count=len(texts), item_count=2310,
                    exact_candidate_sha_join_verified=True,
                    exact_character_and_word_replay_verified=True,
                    text_included=False, model_weights_used=False, new_inference=False)
    return output, bindings


def portable_gzip(payload: bytes) -> bytes:
    target = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0) as stream:
        stream.write(payload)
    return target.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--observations', type=Path)
    parser.add_argument('--qwen-tokenizer', type=Path)
    parser.add_argument('--llama-tokenizer', type=Path)
    parser.add_argument('--output', type=Path, default=HERE)
    parser.add_argument('--main', type=Path)
    parser.add_argument('--transfer', type=Path)
    parser.add_argument('--verify', action='store_true', help='Compare outputs; never overwrite them')
    args = parser.parse_args()
    root = args.root.resolve()
    observations_path = args.observations or root / 'research/option_length_v1/observations.json.gz'
    paths = {'qwen3': args.qwen_tokenizer or root / '.aris/option_length_tokens_v1/tokenizers/qwen3'}
    if args.llama_tokenizer:
        paths['llama32'] = args.llama_tokenizer
    output, bindings = collect(root, observations_path, paths,
                               main_path=args.main, transfer_path=args.transfer)
    payload = compact(output) + b'\n'
    compressed = portable_gzip(payload)
    bindings['artifact'] = dict(path='research/option_length_tokens_v1/token_lengths.json.gz',
                                sha256=hashlib.sha256(compressed).hexdigest(),
                                uncompressed_sha256=hashlib.sha256(payload).hexdigest())
    files = {'token_lengths.json.gz': compressed,
             'bindings.json': (json.dumps(bindings, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')}
    if args.verify:
        for name, content in files.items():
            if (args.output / name).read_bytes() != content:
                raise ValueError('Reproducibility comparison failed: ' + name)
    else:
        if any((args.output / name).exists() for name in files):
            raise FileExistsError('Output exists; use --verify to compare without overwriting')
        args.output.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (args.output / name).write_bytes(content)
    print('Verified CPU-only token counts:', output['candidate_count'], 'candidate hashes,',
          output['item_count'], 'items, references', ','.join(output['tokenizers']))


if __name__ == '__main__':
    main()
