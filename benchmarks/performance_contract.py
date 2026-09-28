"""Freeze/enforce device, software and measurement-code identity before timing."""
import argparse
import importlib.metadata
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from system1bench.common import sha, write  # noqa: E402

SOURCE_FILES = ['benchmarks/performance.py', 'benchmarks/performance_telemetry.py',
                'benchmarks/performance_contract.py', 'system1bench/common.py',
                'system1bench/laya_adapter.py', 'system1bench/llm_adapter.py']
THREAD_ENV = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', TOKENIZERS_PARALLELISM='false')


def environment():
    import torch
    model = next(l.split(':', 1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name'))
    return dict(python=platform.python_version(), kernel=platform.release(), cpu_model=model,
                packages={p: importlib.metadata.version(p) for p in
                          ['torch', 'transformers', 'laya', 'numpy', 'pyarrow', 'huggingface-hub', 'PyYAML']},
                torch_cuda=torch.version.cuda, cudnn_version=torch.backends.cudnn.version(),
                tf32_matmul=torch.backends.cuda.matmul.allow_tf32,
                tf32_cudnn=torch.backends.cudnn.allow_tf32,
                cudnn_benchmark=torch.backends.cudnn.benchmark)


def source_hashes():
    return {p: sha(ROOT / p) for p in SOURCE_FILES}


def validate_contract(contract, manifest_path, gpu):
    if contract['manifest_sha256'] != sha(manifest_path):
        raise ValueError('Run contract manifest changed')
    if contract['source_sha256'] != source_hashes():
        raise ValueError('Measurement/adapter source changed after run-contract freeze')
    if contract['environment'] != environment():
        raise ValueError('Software/kernel/CPU/backend environment changed')
    if any(gpu[k] != v for k, v in contract['device'].items()):
        raise ValueError('GPU identity/driver changed')


def main():
    from benchmarks.performance import gpu_info, now
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', default='performance/v1/manifest.json')
    parser.add_argument('--output', default='performance/v1/run_contract.json')
    parser.add_argument('--gpu', type=int, default=2)
    args = parser.parse_args()
    if Path(args.output).exists():
        raise ValueError('Refuse to overwrite the run contract')
    gpu = gpu_info(args.gpu)
    write(args.output, dict(created_at=now(), manifest_sha256=sha(args.manifest), source_sha256=source_hashes(),
                            protocol_document_sha256=sha(ROOT / 'docs/PERFORMANCE_PROTOCOL.md'),
                            device={k: gpu[k] for k in ['uuid', 'name', 'driver_version', 'memory.total']},
                            environment=environment(), cpu_affinity=[20, 21, 22, 23], cpu_smt_siblings=[84, 85, 86, 87],
                            monitor_cpu_affinity=[24], thread_env=THREAD_ENV,
                            max_other_cpu_busy_fraction=0.15, max_sibling_busy_fraction=0.15,
                            cpu_contention_consecutive_intervals=2))
    print('Frozen hardware/software/code contract:', args.output)


if __name__ == '__main__':
    main()
