"""
Monitoring and Observability Module
Integrates Prometheus metrics, structured logging, and performance tracking
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
import time
import logging
from typing import Callable
from datetime import datetime
import json

# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

# API Request Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

http_request_size_bytes = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint']
)

http_response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint']
)

# Property Metrics
property_searches_total = Counter(
    'property_searches_total',
    'Total property searches',
    ['search_type']  # text, geospatial, filtered
)

property_search_duration_seconds = Histogram(
    'property_search_duration_seconds',
    'Property search duration in seconds',
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0)
)

property_search_results = Histogram(
    'property_search_results',
    'Number of results returned per search',
    buckets=(0, 1, 5, 10, 20, 50, 100, 200, 500, 1000)
)

property_views_total = Counter(
    'property_views_total',
    'Total property views',
    ['property_type', 'listing_type']
)

property_creates_total = Counter(
    'property_creates_total',
    'Total properties created',
    ['property_type', 'listing_type', 'owner_role']
)

property_updates_total = Counter(
    'property_updates_total',
    'Total property updates',
    ['update_type']  # price, photos, status, etc.
)

# User Metrics
user_registrations_total = Counter(
    'user_registrations_total',
    'Total user registrations',
    ['role']
)

user_logins_total = Counter(
    'user_logins_total',
    'Total user logins',
    ['role']
)

user_login_failures_total = Counter(
    'user_login_failures_total',
    'Total failed login attempts',
    ['reason']  # wrong_password, user_not_found, inactive
)

active_sessions = Gauge(
    'active_sessions',
    'Number of active user sessions'
)

# Cache Metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']  # search, property, user
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

cache_operations_duration_seconds = Histogram(
    'cache_operations_duration_seconds',
    'Cache operation duration in seconds',
    ['operation', 'cache_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1)
)

# Database Metrics
db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['query_type', 'table']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Database connection pool size'
)

db_connection_pool_available = Gauge(
    'db_connection_pool_available',
    'Available database connections'
)

# Email Metrics
emails_sent_total = Counter(
    'emails_sent_total',
    'Total emails sent',
    ['email_type', 'status']  # status: success, failed
)

email_send_duration_seconds = Histogram(
    'email_send_duration_seconds',
    'Email send duration in seconds',
    ['email_type']
)

# Background Task Metrics
background_tasks_total = Counter(
    'background_tasks_total',
    'Total background tasks',
    ['task_type', 'status']  # status: success, failed, timeout
)

background_task_duration_seconds = Histogram(
    'background_task_duration_seconds',
    'Background task duration in seconds',
    ['task_type'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

# System Metrics
system_info = Info(
    'system',
    'System information'
)

# Alert-related Metrics
saved_search_alerts_sent_total = Counter(
    'saved_search_alerts_sent_total',
    'Total saved search alerts sent',
    ['alert_type']  # new_listing, price_drop, daily_digest
)

# Error Metrics
errors_total = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'endpoint']
)

# ============================================================================
# MONITORING MIDDLEWARE
# ============================================================================

class PrometheusMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track HTTP requests and responses with Prometheus metrics
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Extract endpoint pattern (remove IDs)
        endpoint = self._clean_endpoint(request.url.path)
        method = request.method
        
        # Track request size
        content_length = request.headers.get('content-length')
        if content_length:
            http_request_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(int(content_length))
        
        # Start timer
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Track response size
            if hasattr(response, 'body'):
                http_response_size_bytes.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(len(response.body))
            
        except Exception as e:
            # Track errors
            errors_total.labels(
                error_type=type(e).__name__,
                endpoint=endpoint
            ).inc()
            raise
        
        finally:
            # Track duration
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            # Track total requests
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()
        
        return response
    
    def _clean_endpoint(self, path: str) -> str:
        """
        Clean endpoint path by removing UUIDs and IDs
        Example: /api/v1/properties/123e4567-e89b-12d3-a456-426614174000 -> /api/v1/properties/{id}
        """
        import re
        
        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{uuid}',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace numeric IDs
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        
        return path


# ============================================================================
# METRICS TRACKING HELPERS
# ============================================================================

class MetricsTracker:
    """Helper class for tracking custom metrics"""
    
    @staticmethod
    def track_search(search_type: str, duration: float, result_count: int):
        """Track property search metrics"""
        property_searches_total.labels(search_type=search_type).inc()
        property_search_duration_seconds.observe(duration)
        property_search_results.observe(result_count)
    
    @staticmethod
    def track_property_view(property_type: str, listing_type: str):
        """Track property view"""
        property_views_total.labels(
            property_type=property_type,
            listing_type=listing_type
        ).inc()
    
    @staticmethod
    def track_property_create(property_type: str, listing_type: str, owner_role: str):
        """Track property creation"""
        property_creates_total.labels(
            property_type=property_type,
            listing_type=listing_type,
            owner_role=owner_role
        ).inc()
    
    @staticmethod
    def track_user_registration(role: str):
        """Track user registration"""
        user_registrations_total.labels(role=role).inc()
    
    @staticmethod
    def track_user_login(role: str, success: bool = True, failure_reason: str = None):
        """Track user login"""
        if success:
            user_logins_total.labels(role=role).inc()
        else:
            user_login_failures_total.labels(reason=failure_reason or 'unknown').inc()
    
    @staticmethod
    def track_cache_operation(cache_type: str, hit: bool, duration: float = None):
        """Track cache hit/miss"""
        if hit:
            cache_hits_total.labels(cache_type=cache_type).inc()
        else:
            cache_misses_total.labels(cache_type=cache_type).inc()
        
        if duration:
            operation = 'hit' if hit else 'miss'
            cache_operations_duration_seconds.labels(
                operation=operation,
                cache_type=cache_type
            ).observe(duration)
    
    @staticmethod
    def track_db_query(query_type: str, table: str, duration: float):
        """Track database query"""
        db_queries_total.labels(query_type=query_type, table=table).inc()
        db_query_duration_seconds.labels(
            query_type=query_type,
            table=table
        ).observe(duration)
    
    @staticmethod
    def track_email(email_type: str, success: bool, duration: float):
        """Track email sending"""
        status = 'success' if success else 'failed'
        emails_sent_total.labels(email_type=email_type, status=status).inc()
        email_send_duration_seconds.labels(email_type=email_type).observe(duration)
    
    @staticmethod
    def track_background_task(task_type: str, success: bool, duration: float):
        """Track background task execution"""
        status = 'success' if success else 'failed'
        background_tasks_total.labels(task_type=task_type, status=status).inc()
        background_task_duration_seconds.labels(task_type=task_type).observe(duration)
    
    @staticmethod
    def set_system_info(version: str, environment: str, python_version: str):
        """Set system information"""
        system_info.info({
            'version': version,
            'environment': environment,
            'python_version': python_version
        })


# ============================================================================
# STRUCTURED LOGGING
# ============================================================================

class StructuredLogger:
    """Structured JSON logger for better observability"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup JSON logging handlers"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s"}'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log(self, level: str, message: str, **kwargs):
        """Log with structured data"""
        log_data = {
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            **kwargs
        }
        
        log_func = getattr(self.logger, level.lower())
        log_func(json.dumps(log_data))
    
    def info(self, message: str, **kwargs):
        self.log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log('ERROR', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self.log('DEBUG', message, **kwargs)


# ============================================================================
# METRICS ENDPOINT
# ============================================================================

async def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus exposition format
    """
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================================================
# HEALTH CHECK
# ============================================================================

async def health_check(db, cache_service) -> dict:
    """
    Comprehensive health check
    Returns system health status
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Database health
    try:
        await db.execute("SELECT 1")
        health_status["checks"]["database"] = {
            "status": "healthy",
            "latency_ms": 0  # Would measure actual latency
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Cache health
    cache_healthy = cache_service.is_available()
    health_status["checks"]["cache"] = {
        "status": "healthy" if cache_healthy else "unhealthy"
    }
    
    if not cache_healthy:
        health_status["status"] = "degraded"
    
    return health_status


# Global metrics tracker instance
metrics_tracker = MetricsTracker()