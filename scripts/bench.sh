#!/usr/bin/env bash
# Internet speed + bufferbloat + router-CPU benchmark.
# Usage: scripts/bench.sh <label>          e.g. scripts/bench.sh before-p1
#        ROUTER=gl-mt6000 scripts/bench.sh after-p1
#
# Produces in ./benchmarks/:
#   <ts>-<label>.speedtest.json   (raw Ookla output)
#   <ts>-<label>.ping.txt         (latency-under-load probe)
#   <ts>-<label>.cpu.txt          (router /proc/loadavg + top samples)
#   <ts>-<label>.summary.txt      (human-readable)
set -euo pipefail

label="${1:-bench}"
router="${ROUTER:-gl-mt6000}"
inventory="${INVENTORY:-$(dirname "$0")/../inventory/hosts.yml}"
ts="$(date +%Y%m%d-%H%M%S)"
out_dir="$(dirname "$0")/../benchmarks"
mkdir -p "$out_dir"
prefix="$out_dir/${ts}-${label}"

ping_log="${prefix}.ping.txt"
st_log="${prefix}.speedtest.json"
cpu_log="${prefix}.cpu.txt"
summary="${prefix}.summary.txt"

echo "==> [$label] starting probes (router=$router)"

# --- Latency-under-load probe (bufferbloat) ---
( ping -i 0.2 -w 70 1.1.1.1 > "$ping_log" 2>&1 ) &
ping_pid=$!

# --- Router CPU sampler (1s interval for 60s) ---
(
  ansible -i "$inventory" "$router" -m raw -a '
    for i in $(seq 1 60); do
      echo "--- t=$i $(date +%T) ---"
      cat /proc/loadavg
      top -bn1 | head -5
      sleep 1
    done
  ' 2>/dev/null > "$cpu_log"
) &
cpu_pid=$!

# small head start so probes are running when speedtest spins up
sleep 2

echo "==> [$label] speedtest (this saturates the link for ~30s)..."
speedtest-cli --json --secure > "$st_log" || echo "{}" > "$st_log"

# stop probes (SIGINT so ping prints its rtt summary line)
kill -INT "$ping_pid" 2>/dev/null || true
wait "$ping_pid" 2>/dev/null || true
wait "$cpu_pid"  2>/dev/null || true

# --- Parse (defensive: never abort on missing data) ---
set +e
dl=$(jq -r '(.download // 0) / 1e6' "$st_log" 2>/dev/null)
ul=$(jq -r '(.upload   // 0) / 1e6' "$st_log" 2>/dev/null)
pg=$(jq -r '.ping     // 0'         "$st_log" 2>/dev/null)

# ping rtt min/avg/max/mdev line (handle both 'rtt' and 'round-trip' forms)
rtt=$(grep -E '^(rtt|round-trip).*min/avg' "$ping_log" | tail -1 \
       | sed -E 's/.*= *([0-9./]+) *ms.*/\1/')
loaded_min=$(echo "$rtt"  | cut -d/ -f1)
loaded_avg=$(echo "$rtt"  | cut -d/ -f2)
loaded_max=$(echo "$rtt"  | cut -d/ -f3)
loaded_mdev=$(echo "$rtt" | cut -d/ -f4)

# router CPU: parse loadavg peak + idle% min (busybox top: "100% idle")
load_peak=$(awk '/^[0-9]+\.[0-9]+ +[0-9]/{print $1}' "$cpu_log" 2>/dev/null | sort -gr | head -1)
cpu_idle_min=$(grep -oE '[0-9]+% *idle' "$cpu_log" 2>/dev/null | grep -oE '[0-9]+' | sort -g | head -1)
sirq_max=$(grep -oE '[0-9]+% *sirq' "$cpu_log" 2>/dev/null | grep -oE '[0-9]+' | sort -gr | head -1)
cpu_used_max=$(awk -v idle="${cpu_idle_min:-100}" 'BEGIN{printf "%.1f", 100-idle}')
set -e

{
  echo "label:         $label"
  echo "timestamp:     $ts"
  echo "router:        $router"
  echo "---- throughput ----"
  printf "download:      %.2f Mbit/s\n" "$dl"
  printf "upload:        %.2f Mbit/s\n" "$ul"
  echo "---- latency ----"
  printf "idle ping:     %.2f ms (speedtest server)\n" "$pg"
  echo "loaded ping:   min=${loaded_min}ms avg=${loaded_avg}ms max=${loaded_max}ms mdev=${loaded_mdev}ms (1.1.1.1 during load)"
  echo "---- router cpu ----"
  echo "load peak (1m): ${load_peak:-n/a}"
  echo "cpu used peak:  ${cpu_used_max}% (idle min=${cpu_idle_min:-n/a}%)"
  echo "softirq peak:   ${sirq_max:-n/a}% (network processing — should drop with flow_offloading)"
} | tee "$summary"

echo
echo "saved:"
echo "  $st_log"
echo "  $ping_log"
echo "  $cpu_log"
echo "  $summary"
