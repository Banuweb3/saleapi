import os
import time
import logging
from logging.handlers import RotatingFileHandler
from flask import request, g

class RequestLoggerAdapter(logging.LoggerAdapter):
    """Custom adapter to safely provide fallback default values for format string keys."""
    def process(self, msg, kwargs):
        extra = self.extra.copy()
        if "extra" in kwargs:
            extra.update(kwargs["extra"])
        extra.setdefault("remote_addr", "127.0.0.1")
        extra.setdefault("method", "-")
        extra.setdefault("url", "-")
        extra.setdefault("status", "-")
        extra.setdefault("duration", "0.0")
        kwargs["extra"] = extra
        return msg, kwargs

def setup_request_logger(app):
    """
    Production-ready request logging middleware.
    Logs HTTP method, requested URL, status code, client IP, and response time (ms).
    Outputs both to stdout and to a rotating log file (logs/production.log).
    """
    log_dir = os.path.join(app.root_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "production.log")

    logger = logging.getLogger("saleapi_production")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s | IP: %(remote_addr)s | Method: %(method)s | Path: %(url)s | Status: %(status)s | Duration: %(duration)s ms'
        )

        # Rotating file handler (10MB per log file, max 5 backups)
        file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console stream handler
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    adapted_logger = RequestLoggerAdapter(logger, {})

    @app.before_request
    def start_request_timer():
        g.start_time = time.time()

    @app.after_request
    def log_response_info(response):
        # Calculate execution duration in milliseconds
        start_time = getattr(g, "start_time", None)
        duration = round((time.time() - start_time) * 1000, 2) if start_time else 0.0

        # Extract client IP address (supporting reverse proxy X-Forwarded-For)
        client_ip = request.headers.get("X-Forwarded-For")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.remote_addr or "127.0.0.1"

        extra_info = {
            "remote_addr": client_ip,
            "method": request.method,
            "url": request.path,
            "status": response.status_code,
            "duration": str(duration)
        }

        adapted_logger.info(
            f"Handled {request.method} {request.path} [{response.status_code}] in {duration}ms",
            extra=extra_info
        )

        return response
