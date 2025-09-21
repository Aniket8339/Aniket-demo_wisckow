#!/usr/bin/env python3
"""
System Health Monitoring Script
Monitors CPU usage, memory usage, disk space, and running processes.
Sends alerts when metrics exceed predefined thresholds.
"""

import psutil
import time
import logging
import smtplib
from email.mime.text import MimeText
from datetime import datetime
import json
import os

class SystemHealthMonitor:
    def __init__(self, config_file="monitor_config.json"):
        # Default thresholds
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "max_processes": 300
        }
        
        # Load configuration if exists
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.thresholds.update(config.get('thresholds', {}))
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('system_health.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_cpu_usage(self):
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=1)
    
    def get_memory_usage(self):
        """Get current memory usage"""
        memory = psutil.virtual_memory()
        return {
            'percent': memory.percent,
            'used': self.bytes_to_gb(memory.used),
            'total': self.bytes_to_gb(memory.total),
            'available': self.bytes_to_gb(memory.available)
        }
    
    def get_disk_usage(self):
        """Get disk usage for all mounted drives"""
        disk_info = {}
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info[partition.mountpoint] = {
                    'percent': (usage.used / usage.total) * 100,
                    'used': self.bytes_to_gb(usage.used),
                    'total': self.bytes_to_gb(usage.total),
                    'free': self.bytes_to_gb(usage.free)
                }
            except PermissionError:
                continue
        return disk_info
    
    def get_process_count(self):
        """Get current number of running processes"""
        return len(psutil.pids())
    
    def get_top_processes(self, limit=5):
        """Get top processes by CPU usage"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:limit]
    
    def bytes_to_gb(self, bytes_value):
        """Convert bytes to GB"""
        return round(bytes_value / (1024**3), 2)
    
    def send_alert(self, alert_type, message):
        """Send alert to console and log file"""
        alert_msg = f"🚨 ALERT [{alert_type}]: {message}"
        self.logger.warning(alert_msg)
        print(f"\n{alert_msg}\n")
    
    def check_thresholds(self, metrics):
        """Check if any metrics exceed thresholds"""
        alerts = []
        
        # CPU check
        if metrics['cpu_percent'] > self.thresholds['cpu_percent']:
            alerts.append(f"High CPU usage: {metrics['cpu_percent']:.1f}% (threshold: {self.thresholds['cpu_percent']}%)")
        
        # Memory check
        if metrics['memory']['percent'] > self.thresholds['memory_percent']:
            alerts.append(f"High memory usage: {metrics['memory']['percent']:.1f}% (threshold: {self.thresholds['memory_percent']}%)")
        
        # Disk check
        for mount, disk_data in metrics['disk'].items():
            if disk_data['percent'] > self.thresholds['disk_percent']:
                alerts.append(f"High disk usage on {mount}: {disk_data['percent']:.1f}% (threshold: {self.thresholds['disk_percent']}%)")
        
        # Process count check
        if metrics['process_count'] > self.thresholds['max_processes']:
            alerts.append(f"High process count: {metrics['process_count']} (threshold: {self.thresholds['max_processes']})")
        
        return alerts
    
    def generate_report(self, metrics):
        """Generate a comprehensive system health report"""
        report = f"""
=== SYSTEM HEALTH REPORT ===
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CPU Usage: {metrics['cpu_percent']:.1f}%
Memory Usage: {metrics['memory']['percent']:.1f}% ({metrics['memory']['used']} GB / {metrics['memory']['total']} GB)

Disk Usage:"""
        
        for mount, disk_data in metrics['disk'].items():
            report += f"\n  {mount}: {disk_data['percent']:.1f}% ({disk_data['used']} GB / {disk_data['total']} GB)"
        
        report += f"\n\nRunning Processes: {metrics['process_count']}"
        report += f"\n\nTop 5 Processes by CPU:"
        for proc in metrics['top_processes']:
            report += f"\n  PID {proc['pid']}: {proc['name']} - CPU: {proc['cpu_percent'] or 0:.1f}%, Memory: {proc['memory_percent'] or 0:.1f}%"
        
        return report
    
    def monitor_once(self):
        """Perform one monitoring cycle"""
        metrics = {
            'cpu_percent': self.get_cpu_usage(),
            'memory': self.get_memory_usage(),
            'disk': self.get_disk_usage(),
            'process_count': self.get_process_count(),
            'top_processes': self.get_top_processes()
        }
        
        # Check for alerts
        alerts = self.check_thresholds(metrics)
        for alert in alerts:
            self.send_alert("THRESHOLD_EXCEEDED", alert)
        
        # Log current status
        report = self.generate_report(metrics)
        self.logger.info("System health check completed")
        
        return metrics, alerts, report
    
    def monitor_continuous(self, interval=60):
        """Run continuous monitoring"""
        self.logger.info(f"Starting continuous monitoring (interval: {interval}s)")
        self.logger.info(f"Thresholds: {self.thresholds}")
        
        try:
            while True:
                metrics, alerts, report = self.monitor_once()
                
                if not alerts:
                    print(f"✅ System healthy - {datetime.now().strftime('%H:%M:%S')}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
            print("\n🛑 Monitoring stopped")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='System Health Monitor')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in seconds (default: 60)')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    
    args = parser.parse_args()
    
    monitor = SystemHealthMonitor()
    
    if args.once or args.report:
        metrics, alerts, report = monitor.monitor_once()
        if args.report:
            print(report)
    else:
        monitor.monitor_continuous(args.interval)

if __name__ == "__main__":
    main()