import psutil
import subprocess
import time
from typing import Optional

def get_cpu_metrics() -> dict:
    freq = psutil.cpu_freq()
    return {
        "percent": psutil.cpu_percent(interval=0.5),
        "per_core": psutil.cpu_percent(interval=0.5, percpu=True),
        "freq_mhz": round(freq.current, 1) if freq else 0,
        "count_logical": psutil.cpu_count(logical=True),
        "count_physical": psutil.cpu_count(logical=False),
    }

def get_memory_metrics() -> dict:
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    return {
        "percent": vm.percent,
        "used_gb": round(vm.used / 1e9, 2),
        "available_gb": round(vm.available / 1e9, 2),
        "total_gb": round(vm.total / 1e9, 2),
        "swap_percent": sw.percent,
        "swap_used_gb": round(sw.used / 1e9, 2),
        "swap_total_gb": round(sw.total / 1e9, 2),
    }

def get_disk_metrics() -> dict:
    usage = psutil.disk_usage("/")
    io = psutil.disk_io_counters()
    return {
        "percent": usage.percent,
        "used_gb": round(usage.used / 1e9, 2),
        "total_gb": round(usage.total / 1e9, 2),
        "read_mb": round(io.read_bytes / 1e6, 2) if io else 0,
        "write_mb": round(io.write_bytes / 1e6, 2) if io else 0,
        "read_count": io.read_count if io else 0,
        "write_count": io.write_count if io else 0,
    }

def get_network_metrics() -> dict:
    net = psutil.net_io_counters()
    return {
        "sent_mb": round(net.bytes_sent / 1e6, 2),
        "recv_mb": round(net.bytes_recv / 1e6, 2),
        "packets_sent": net.packets_sent,
        "packets_recv": net.packets_recv,
    }

def get_load_average() -> dict:
    load = psutil.getloadavg()
    return {"avg_1": load[0], "avg_5": load[1], "avg_15": load[2]}

def get_top_processes(n: int = 10) -> list:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(procs, key=lambda x: x["cpu_percent"] or 0, reverse=True)[:n]

def get_io_wait() -> Optional[float]:
    """Parse IO wait from /proc/stat."""
    try:
        with open("/proc/stat") as f:
            line = f.readline()
        fields = line.split()
        # fields: user nice system idle iowait ...
        total = sum(int(x) for x in fields[1:])
        iowait = int(fields[5])
        return round((iowait / total) * 100, 2) if total else 0.0
    except Exception:
        return None

def collect_all() -> dict:
    return {
        "timestamp": time.time(),
        "cpu": get_cpu_metrics(),
        "memory": get_memory_metrics(),
        "disk": get_disk_metrics(),
        "network": get_network_metrics(),
        "load": get_load_average(),
        "io_wait": get_io_wait(),
        "processes": get_top_processes(),
    }
