"""
System monitoring utilities for real-time dashboard metrics
"""
import time
import psutil
from django.db import connection
from django.core.cache import cache


class SystemMonitor:
    """Real-time system monitoring for dashboard health metrics"""
    
    @staticmethod
    def get_memory_usage():
        """Get current memory usage percentage"""
        try:
            memory = psutil.virtual_memory()
            return round(memory.percent, 1)
        except Exception:
            return 0.0
    
    @staticmethod
    def get_cpu_usage():
        """Get current CPU usage percentage"""
        try:
            return round(psutil.cpu_percent(interval=1), 1)
        except Exception:
            return 0.0
    
    @staticmethod
    def get_disk_usage():
        """Get current disk usage percentage"""
        try:
            disk = psutil.disk_usage('/')
            return round((disk.used / disk.total) * 100, 1)
        except Exception:
            return 0.0
    
    @staticmethod
    def get_database_status():
        """Check database connection and get status"""
        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            # Get database connection info
            db_queries_count = len(connection.queries)
            
            return {
                'status': 'healthy',
                'queries_count': db_queries_count,
                'connection_alive': True
            }
        except Exception as e:
            return {
                'status': 'error',
                'queries_count': 0,
                'connection_alive': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_active_connections():
        """Get approximate number of active database connections"""
        try:
            # For SQLite, we can't get real connection count
            # For PostgreSQL, you could query pg_stat_activity
            if 'postgresql' in str(connection.settings_dict.get('ENGINE', '')):
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT count(*) 
                        FROM pg_stat_activity 
                        WHERE state = 'active'
                    """)
                    return cursor.fetchone()[0]
            else:
                # For SQLite or other DBs, return a reasonable estimate
                return max(1, len(connection.queries))
        except Exception:
            return 1
    
    @staticmethod
    def measure_api_response_time(func, *args, **kwargs):
        """Measure API response time for a function"""
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)  # Convert to milliseconds
            return result, response_time
        except Exception as e:
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            raise e
    
    @staticmethod
    def get_system_load():
        """Get system load averages"""
        try:
            load_avg = psutil.getloadavg()
            return {
                '1min': round(load_avg[0], 2),
                '5min': round(load_avg[1], 2),
                '15min': round(load_avg[2], 2)
            }
        except (AttributeError, Exception):
            # getloadavg() might not be available on all systems
            return {
                '1min': 0.0,
                '5min': 0.0,
                '15min': 0.0
            }
    
    @staticmethod
    def get_network_stats():
        """Get network I/O statistics"""
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
        except Exception:
            return {
                'bytes_sent': 0,
                'bytes_recv': 0,
                'packets_sent': 0,
                'packets_recv': 0
            }
    
    @classmethod
    def get_comprehensive_health(cls):
        """Get comprehensive system health metrics"""
        start_time = time.time()
        
        # Get all metrics
        memory_usage = cls.get_memory_usage()
        cpu_usage = cls.get_cpu_usage()
        disk_usage = cls.get_disk_usage()
        db_status = cls.get_database_status()
        active_connections = cls.get_active_connections()
        system_load = cls.get_system_load()
        network_stats = cls.get_network_stats()
        
        # Calculate this operation's response time
        response_time = round((time.time() - start_time) * 1000, 2)
        
        # Determine overall health status
        overall_status = 'healthy'
        if memory_usage > 90 or cpu_usage > 90 or disk_usage > 90:
            overall_status = 'critical'
        elif memory_usage > 80 or cpu_usage > 80 or disk_usage > 80:
            overall_status = 'warning'
        elif not db_status['connection_alive']:
            overall_status = 'critical'
        
        return {
            'overall_status': overall_status,
            'api_response_time': response_time,
            'memory_usage': memory_usage,
            'cpu_usage': cpu_usage,
            'disk_usage': disk_usage,
            'database_status': db_status['status'],
            'active_connections': active_connections,
            'system_load': system_load,
            'network_stats': network_stats,
            'timestamp': time.time()
        }
    
    @classmethod
    def get_cached_health(cls, cache_duration=30):
        """Get health metrics with caching to avoid excessive system calls"""
        cache_key = 'system_health_metrics'
        cached_data = cache.get(cache_key)
        
        if cached_data is None:
            cached_data = cls.get_comprehensive_health()
            cache.set(cache_key, cached_data, cache_duration)
        
        return cached_data