"""
System Monitor Agent - Monitors system resources for dynamic scaling.

Extracted from agent_crew.py - this is the only class used by formai_server.py.
"""

import logging
import psutil
import threading
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger("system-monitor")

# System resource thresholds for scaling
CPU_THRESHOLD_HIGH = 80  # Above this, don't spawn more agents
MEMORY_THRESHOLD = 80    # Max memory usage percentage
MAX_PARALLEL_AGENTS = 10  # Maximum parallel browser instances


class SystemMonitorAgent:
    """
    System Monitor Agent - Monitors system resources to enable dynamic scaling.

    Responsibilities:
    - Monitor CPU usage
    - Monitor memory usage
    - Track network activity
    - Count active threads/processes
    - Recommend whether to spawn more parallel agents

    This enables the system to dynamically scale based on available resources.
    """

    def __init__(self):
        self.name = "SystemMonitorAgent"
        self._last_check = None
        self._cached_metrics = None
        self._active_agents = 0

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            # CPU usage (average over 0.1 second)
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Network I/O
            net_io = psutil.net_io_counters()

            # Process info
            current_process = psutil.Process()
            process_threads = current_process.num_threads()
            process_memory = current_process.memory_info().rss / (1024 * 1024)  # MB

            # Count Python threads in current process
            active_threads = threading.active_count()

            # Chrome/browser processes (if any)
            browser_processes = 0
            for proc in psutil.process_iter(['name']):
                try:
                    if 'chrome' in proc.info['name'].lower() or 'playwright' in proc.info['name'].lower():
                        browser_processes += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
                    pass

            metrics = {
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory_percent, 1),
                "memory_available_mb": round(memory.available / (1024 * 1024), 0),
                "network_bytes_sent": net_io.bytes_sent,
                "network_bytes_recv": net_io.bytes_recv,
                "process_threads": process_threads,
                "active_threads": active_threads,
                "process_memory_mb": round(process_memory, 1),
                "browser_processes": browser_processes,
                "timestamp": datetime.now().isoformat()
            }

            self._cached_metrics = metrics
            self._last_check = datetime.now()
            return metrics

        except Exception as e:
            logger.error(f"[{self.name}] Error getting metrics: {e}")
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "error": str(e)
            }

    def can_spawn_more_agents(self, current_agents: int = 0) -> Dict[str, Any]:
        """
        Determine if system can handle more parallel agents.

        Returns:
            {
                "can_spawn": True/False,
                "max_additional": int,
                "reason": str,
                "metrics": {...}
            }
        """
        self._active_agents = current_agents
        metrics = self.get_system_metrics()

        cpu = metrics.get("cpu_percent", 100)
        memory = metrics.get("memory_percent", 100)

        # Check limits
        if current_agents >= MAX_PARALLEL_AGENTS:
            return {
                "can_spawn": False,
                "max_additional": 0,
                "reason": f"Max agents reached ({MAX_PARALLEL_AGENTS})",
                "metrics": metrics
            }

        if cpu >= CPU_THRESHOLD_HIGH:
            return {
                "can_spawn": False,
                "max_additional": 0,
                "reason": f"CPU too high ({cpu}%)",
                "metrics": metrics
            }

        if memory >= MEMORY_THRESHOLD:
            return {
                "can_spawn": False,
                "max_additional": 0,
                "reason": f"Memory too high ({memory}%)",
                "metrics": metrics
            }

        # Calculate how many more we can spawn
        # Each browser instance uses roughly 200-400MB RAM and 5-15% CPU
        available_cpu_headroom = CPU_THRESHOLD_HIGH - cpu
        available_memory_mb = metrics.get("memory_available_mb", 0)

        # Conservative estimate: each agent needs 10% CPU and 300MB RAM
        max_by_cpu = int(available_cpu_headroom / 10)
        max_by_memory = int(available_memory_mb / 300)
        max_by_limit = MAX_PARALLEL_AGENTS - current_agents

        max_additional = min(max_by_cpu, max_by_memory, max_by_limit)
        max_additional = max(0, max_additional)

        if max_additional > 0:
            return {
                "can_spawn": True,
                "max_additional": max_additional,
                "reason": f"Resources available (CPU: {cpu}%, MEM: {memory}%)",
                "recommended": min(max_additional, 2),  # Spawn 1-2 at a time
                "metrics": metrics
            }
        else:
            return {
                "can_spawn": False,
                "max_additional": 0,
                "reason": "No headroom for additional agents",
                "metrics": metrics
            }

    def get_performance_report(self) -> str:
        """Get a human-readable performance report."""
        metrics = self.get_system_metrics()

        report = [
            f"=== System Performance Report ===",
            f"CPU: {metrics.get('cpu_percent', '?')}%",
            f"Memory: {metrics.get('memory_percent', '?')}%",
            f"Available Memory: {metrics.get('memory_available_mb', '?')} MB",
            f"Process Threads: {metrics.get('process_threads', '?')}",
            f"Active Threads: {metrics.get('active_threads', '?')}",
            f"Browser Processes: {metrics.get('browser_processes', '?')}",
            f"Process Memory: {metrics.get('process_memory_mb', '?')} MB",
        ]

        # Add scaling recommendation
        scaling = self.can_spawn_more_agents(self._active_agents)
        if scaling["can_spawn"]:
            report.append(f"Scaling: Can spawn up to {scaling['max_additional']} more agents")
        else:
            report.append(f"Scaling: {scaling['reason']}")

        return "\n".join(report)

    def log_metrics(self):
        """Log current metrics to console."""
        metrics = self.get_system_metrics()
        print(f"[{self.name}] CPU: {metrics.get('cpu_percent')}% | "
              f"MEM: {metrics.get('memory_percent')}% | "
              f"Threads: {metrics.get('active_threads')} | "
              f"Browsers: {metrics.get('browser_processes')}")
