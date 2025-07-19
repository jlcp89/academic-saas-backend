import psutil
import platform
import time
from django.db import connection
from django.core.cache import cache
from typing import Dict, Any


class SystemMonitor:
    """System monitoring utilities for dashboard metrics"""
    
    @staticmethod
    def get_system_health() -> Dict[str, Any]:
        """Get comprehensive system health metrics"""
        return {
            'overall_status': SystemMonitor.get_overall_status(),
            'api_response_time': SystemMonitor.get_api_response_time(),
            'current_request_time': time.time(),
            'memory_usage': SystemMonitor.get_memory_usage(),
            'cpu_usage': SystemMonitor.get_cpu_usage(),
            'disk_usage': SystemMonitor.get_disk_usage(),
            'database_status': SystemMonitor.get_database_status(),
            'active_connections': SystemMonitor.get_active_connections(),
            'system_load': SystemMonitor.get_system_load(),
            'network_stats': SystemMonitor.get_network_stats(),
            'timestamp': int(time.time()),
        }
    
    @staticmethod
    def get_memory_usage() -> float:
        """Get memory usage percentage"""
        try:
            memory = psutil.virtual_memory()
            return round(memory.percent, 2)
        except Exception:
            return 0.0
    
    @staticmethod
    def get_cpu_usage() -> float:
        """Get CPU usage percentage"""
        try:
            return round(psutil.cpu_percent(interval=1), 2)
        except Exception:
            return 0.0
    
    @staticmethod
    def get_disk_usage() -> float:
        """Get disk usage percentage"""
        try:
            disk = psutil.disk_usage('/')
            return round(disk.percent, 2)
        except Exception:
            return 0.0
    
    @staticmethod
    def get_database_status() -> str:
        """Check database connectivity and status"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return 'healthy'
        except Exception:
            return 'error'
    
    @staticmethod
    def get_active_connections() -> int:
        """Get number of active database connections"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """)
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception:
            return 0
    
    @staticmethod
    def get_system_load() -> Dict[str, float]:
        """Get system load averages"""
        try:
            if platform.system() != 'Windows':
                load1, load5, load15 = psutil.getloadavg()
                return {
                    '1min': round(load1, 2),
                    '5min': round(load5, 2),
                    '15min': round(load15, 2),
                }
            else:
                # Windows doesn't have load averages
                cpu_percent = psutil.cpu_percent()
                return {
                    '1min': round(cpu_percent / 100, 2),
                    '5min': round(cpu_percent / 100, 2),
                    '15min': round(cpu_percent / 100, 2),
                }
        except Exception:
            return {'1min': 0.0, '5min': 0.0, '15min': 0.0}
    
    @staticmethod
    def get_network_stats() -> Dict[str, int]:
        """Get network statistics"""
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
            }
        except Exception:
            return {
                'bytes_sent': 0,
                'bytes_recv': 0,
                'packets_sent': 0,
                'packets_recv': 0,
            }
    
    @staticmethod
    def get_api_response_time() -> float:
        """Get average API response time from cache"""
        try:
            response_time = cache.get('avg_response_time', 0.0)
            return round(response_time, 3)
        except Exception:
            return 0.0
    
    @staticmethod
    def get_overall_status() -> str:
        """Determine overall system status based on metrics"""
        try:
            memory_usage = SystemMonitor.get_memory_usage()
            cpu_usage = SystemMonitor.get_cpu_usage()
            disk_usage = SystemMonitor.get_disk_usage()
            db_status = SystemMonitor.get_database_status()
            
            if db_status == 'error':
                return 'critical'
            
            if memory_usage > 90 or cpu_usage > 90 or disk_usage > 95:
                return 'critical'
            
            if memory_usage > 80 or cpu_usage > 80 or disk_usage > 85:
                return 'warning'
            
            return 'healthy'
        except Exception:
            return 'warning'