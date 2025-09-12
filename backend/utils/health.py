"""Health check and monitoring utilities"""

import time
import psutil
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from utils.logger import get_logger
from utils.cache import cache_manager
from config import config

logger = get_logger(__name__)

class HealthChecker:
    """System health monitoring"""
    
    def __init__(self):
        self.start_time = time.time()
        self.checks = {}
        self.last_check = {}
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                }
            }
        except Exception as e:
            logger.error(f"Failed to check system resources: {e}")
            return {'error': str(e)}
    
    def check_database_connection(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            client = chromadb.PersistentClient(
                path=config.get('CHROMA_DB_PATH'),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Try to list collections
            collections = client.list_collections()
            
            return {
                'status': 'healthy',
                'collections_count': len(collections),
                'database_path': config.get('CHROMA_DB_PATH')
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_openai_connection(self) -> Dict[str, Any]:
        """Check OpenAI API connectivity"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=config.get('OPENAI_API_KEY'))
            
            # Make a simple API call
            response = client.models.list()
            
            return {
                'status': 'healthy',
                'models_available': len(response.data) if response.data else 0
            }
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_cache_health(self) -> Dict[str, Any]:
        """Check cache system health"""
        try:
            stats = cache_manager.get_stats()
            
            # Test cache operations
            test_key = f"health_check_{int(time.time())}"
            test_value = "test_value"
            
            cache_manager.set(test_key, test_value, ttl=60)
            retrieved_value = cache_manager.get(test_key)
            cache_manager.delete(test_key)
            
            return {
                'status': 'healthy',
                'stats': stats,
                'test_passed': retrieved_value == test_value
            }
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def get_uptime(self) -> Dict[str, Any]:
        """Get application uptime"""
        uptime_seconds = time.time() - self.start_time
        uptime_delta = timedelta(seconds=int(uptime_seconds))
        
        return {
            'uptime_seconds': uptime_seconds,
            'uptime_human': str(uptime_delta),
            'start_time': datetime.fromtimestamp(self.start_time).isoformat()
        }
    
    def run_health_check(self, check_name: str) -> Dict[str, Any]:
        """Run a specific health check"""
        check_methods = {
            'system': self.check_system_resources,
            'database': self.check_database_connection,
            'openai': self.check_openai_connection,
            'cache': self.check_cache_health,
            'uptime': self.get_uptime
        }
        
        if check_name not in check_methods:
            return {'error': f'Unknown health check: {check_name}'}
        
        try:
            result = check_methods[check_name]()
            self.last_check[check_name] = {
                'timestamp': time.time(),
                'result': result
            }
            return result
        except Exception as e:
            logger.error(f"Health check {check_name} failed: {e}")
            return {'error': str(e)}
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        
        for check_name in ['system', 'database', 'openai', 'cache', 'uptime']:
            results[check_name] = self.run_health_check(check_name)
        
        # Determine overall health
        unhealthy_checks = [
            name for name, result in results.items()
            if 'error' in result or result.get('status') == 'unhealthy'
        ]
        
        overall_status = 'healthy' if not unhealthy_checks else 'unhealthy'
        
        return {
            'overall_status': overall_status,
            'unhealthy_checks': unhealthy_checks,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': results
        }

class MetricsCollector:
    """Application metrics collection"""
    
    def __init__(self):
        self.metrics = {
            'requests_total': 0,
            'requests_successful': 0,
            'requests_failed': 0,
            'queries_total': 0,
            'queries_successful': 0,
            'queries_failed': 0,
            'repositories_indexed': 0,
            'conversations_created': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_response_time': 0,
            'response_times': []
        }
        self.start_time = time.time()
    
    def increment_counter(self, metric_name: str, value: int = 1):
        """Increment a counter metric"""
        if metric_name in self.metrics:
            self.metrics[metric_name] += value
    
    def record_response_time(self, response_time: float):
        """Record response time"""
        self.metrics['response_times'].append(response_time)
        
        # Keep only last 1000 response times
        if len(self.metrics['response_times']) > 1000:
            self.metrics['response_times'] = self.metrics['response_times'][-1000:]
        
        # Update average
        self.metrics['average_response_time'] = sum(self.metrics['response_times']) / len(self.metrics['response_times'])
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        uptime = time.time() - self.start_time
        
        return {
            **self.metrics,
            'uptime_seconds': uptime,
            'requests_per_second': self.metrics['requests_total'] / uptime if uptime > 0 else 0,
            'success_rate': (
                self.metrics['requests_successful'] / self.metrics['requests_total']
                if self.metrics['requests_total'] > 0 else 0
            ),
            'query_success_rate': (
                self.metrics['queries_successful'] / self.metrics['queries_total']
                if self.metrics['queries_total'] > 0 else 0
            )
        }
    
    def reset_metrics(self):
        """Reset all metrics"""
        for key in self.metrics:
            if isinstance(self.metrics[key], list):
                self.metrics[key] = []
            else:
                self.metrics[key] = 0
        self.start_time = time.time()

# Global instances
health_checker = HealthChecker()
metrics_collector = MetricsCollector()
