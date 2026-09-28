"""Out-of-process telemetry, pinned away from measured CPU cores and SMT siblings."""
import argparse
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.performance import foreign_gpu_pids, gpu_info, now, save_gzip  # noqa: E402
from system1bench.common import read, write  # noqa: E402


def cpu_snapshot(pid, cores):
    stats = {}
    for line in Path('/proc/stat').read_text().splitlines():
        fields = line.split()
        if fields[0].startswith('cpu') and fields[0][3:].isdigit() and int(fields[0][3:]) in cores:
            v = list(map(int, fields[1:9]))
            stats[int(fields[0][3:])] = dict(total=sum(v), busy=sum(v) - v[3] - v[4])
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    # fields[0] is /proc stat field 3 (state); 14/15 are process utime/stime.
    ticks = int(fields[11]) + int(fields[12])
    status = {}
    for line in Path(f'/proc/{pid}/status').read_text().splitlines():
        if line.startswith(('voluntary_ctxt_switches:', 'nonvoluntary_ctxt_switches:')):
            key, val = line.split(':')
            status[key] = int(val.strip())
    return dict(cores=stats, process_cpu_ticks=ticks, main_thread_context_switches=status,
                monotonic=time.perf_counter())


def cpu_delta(previous, current, measured, siblings):
    elapsed = current['monotonic'] - previous['monotonic']
    hz = os.sysconf('SC_CLK_TCK')
    busy = {c: (current['cores'][c]['busy'] - previous['cores'][c]['busy']) / hz for c in measured + siblings}
    own = (current['process_cpu_ticks'] - previous['process_cpu_ticks']) / hz
    return dict(interval_seconds=elapsed, core_busy_fraction={str(c): busy[c] / elapsed for c in busy},
                worker_cpu_seconds=own,
                other_busy_fraction_on_worker_cores=max(0, sum(busy[c] for c in measured) - own) / (elapsed * len(measured)),
                smt_sibling_busy_fraction=sum(busy[c] for c in siblings) / (elapsed * len(siblings)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--gpu', type=int, required=True)
    parser.add_argument('--uuid', required=True)
    parser.add_argument('--contract', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    contract = read(args.contract)
    os.sched_setaffinity(0, contract['monitor_cpu_affinity'])
    out = Path(args.output)
    measured, siblings = contract['cpu_affinity'], contract['cpu_smt_siblings']
    stopped = [False]

    def stop(_signal, _frame):
        stopped[0] = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    records, errors, previous, previous_phase, contention_streak = [], [], None, None, 0
    try:
        while not stopped[0] and Path(f'/proc/{args.pid}').exists():
            started = time.perf_counter()
            info = gpu_info(args.gpu)
            if info['uuid'] != args.uuid:
                raise RuntimeError('GPU identity changed')
            foreign = foreign_gpu_pids(args.uuid, args.pid)
            if foreign:
                errors.append('Foreign GPU compute process observed')
            phase = read(out / 'measurement_phase.json') if (out / 'measurement_phase.json').exists() else dict(phase='setup')
            snap = cpu_snapshot(args.pid, measured + siblings)
            record = dict(utc=now(), monotonic=started, gpu=info, foreign_compute_process_count=len(foreign),
                          host_load_average=list(os.getloadavg()), phase=phase, cpu=snap)
            if previous is not None:
                delta = cpu_delta(previous, snap, measured, siblings)
                record['cpu_interval'] = delta
                during_cell = previous_phase == phase and phase['phase'] == 'measured'
                contaminated = (delta['other_busy_fraction_on_worker_cores'] > contract['max_other_cpu_busy_fraction'] or
                                delta['smt_sibling_busy_fraction'] > contract['max_sibling_busy_fraction'])
                contention_streak = contention_streak + 1 if during_cell and contaminated else 0
                if contention_streak >= contract['cpu_contention_consecutive_intervals']:
                    errors.append('Sustained CPU/SMT contention exceeds frozen threshold')
            records.append(record)
            previous, previous_phase = snap, phase
            write(out / 'telemetry_status.json', dict(status='RUNNING', samples=len(records), errors=errors,
                                                     monitor_cpu_affinity=sorted(os.sched_getaffinity(0))))
            while not stopped[0] and time.perf_counter() - started < 1.0:
                time.sleep(0.05)
    except BaseException as exc:
        errors.append(f'{type(exc).__name__}: {exc}')
    finally:
        save_gzip(out / 'telemetry.json.gz', records)
        write(out / 'telemetry_status.json', dict(status='DONE' if not errors else 'FAILED', samples=len(records),
                                                errors=errors, monitor_cpu_affinity=sorted(os.sched_getaffinity(0))))


if __name__ == '__main__':
    main()
