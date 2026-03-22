import psutil
from datetime import datetime
import time

def collect_snapshot() -> dict:
    cpu = psutil.cpu_percent(interval=1)
    
    ram = psutil.virtual_memory()
    ram_used_percent = ram.percent
    ram_used_mb = ram.used / (1024 ** 2)
    ram_total_mb = ram.total / (1024 ** 2)

    disk = psutil.disk_usage("/")
    disk_used_percent = disk.percent
    disk_used_gb = disk.used / (1024 ** 3)
    disk_total_gb = disk.total / (1024 ** 3)

    timestamp = datetime.now().isoformat()

    return {
        "timestamp": timestamp,
        "cpu_percent": cpu,
        "ram_percent": ram_used_percent,
        "ram_used_mb": round(ram_used_mb, 2),
        "ram_total_mb": round(ram_total_mb, 2),
        "disk_percent": disk_used_percent,
        "disk_used_gb": round(disk_used_gb, 2),
        "disk_total_gb": round(disk_total_gb, 2),
    }

def collect_loop(interval_seconds: int =5, rounds: int=3) -> None:
    print(f"Collecting every {interval_seconds}s for {rounds} rounds...\n")
    for i in range(rounds):
        snapshot = collect_snapshot()
        print(f"[Round {i+1}] {snapshot['timestamp']}")
        print(f"  CPU: {snapshot['cpu_percent']}%")
        print(f"  RAM: {snapshot['ram_percent']}%  ({snapshot['ram_used_mb']} MB used)")
        print(f"  Disk: {snapshot['disk_percent']}%  ({snapshot['disk_used_gb']} GB used)\n")
        if i < rounds - 1:
            time.sleep(interval_seconds)

if __name__ == "__main__":
    collect_loop(interval_seconds=5, rounds=3)