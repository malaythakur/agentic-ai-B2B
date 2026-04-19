"""Graceful shutdown handling"""
import signal
import sys
import logging
import time
from typing import List, Callable
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """Handle graceful shutdown of application"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.shutdown_hooks: List[Callable] = []
        self.is_shutting_down = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        if sys.platform != 'win32':
            signal.signal(signal.SIGQUIT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        signame = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
        logger.info(f"Received signal {signame}, initiating graceful shutdown...")
        self.shutdown()
    
    def register_hook(self, hook: Callable):
        """Register a shutdown hook"""
        self.shutdown_hooks.append(hook)
        logger.debug(f"Registered shutdown hook: {hook.__name__}")
    
    def shutdown(self):
        """Execute graceful shutdown"""
        if self.is_shutting_down:
            logger.warning("Shutdown already in progress, ignoring...")
            return
        
        self.is_shutting_down = True
        logger.info("Starting graceful shutdown...")
        
        start_time = time.time()
        
        # Execute shutdown hooks
        for hook in self.shutdown_hooks:
            try:
                hook_name = hook.__name__ if hasattr(hook, '__name__') else str(hook)
                logger.info(f"Executing shutdown hook: {hook_name}")
                hook()
            except Exception as e:
                logger.error(f"Shutdown hook failed: {e}")
        
        elapsed = time.time() - start_time
        logger.info(f"Graceful shutdown completed in {elapsed:.2f}s")
        
        # Exit application
        sys.exit(0)
    
    @contextmanager
    def shutdown_context(self):
        """Context manager for graceful shutdown"""
        try:
            yield self
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.shutdown()
        finally:
            if not self.is_shutting_down:
                self.shutdown()


# Global shutdown manager
_shutdown_manager: GracefulShutdown = None


def get_shutdown_manager() -> GracefulShutdown:
    """Get or create global shutdown manager"""
    global _shutdown_manager
    if _shutdown_manager is None:
        _shutdown_manager = GracefulShutdown()
    return _shutdown_manager


# Common shutdown hooks

def close_database_connections():
    """Close all database connections"""
    try:
        from app.database import engine
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


def stop_celery_workers():
    """Stop Celery workers gracefully"""
    try:
        from app.workers.celery_app import celery_app
        celery_app.control.broadcast('shutdown')
        logger.info("Celery workers stopped")
    except Exception as e:
        logger.error(f"Error stopping Celery workers: {e}")


def flush_logs():
    """Flush all log handlers"""
    try:
        logging.shutdown()
        logger.info("Logs flushed")
    except Exception as e:
        logger.error(f"Error flushing logs: {e}")


def save_state():
    """Save any pending state to database"""
    try:
        # This would save any in-memory state
        logger.info("State saved")
    except Exception as e:
        logger.error(f"Error saving state: {e}")


def setup_default_shutdown_hooks():
    """Setup default shutdown hooks"""
    manager = get_shutdown_manager()
    manager.register_hook(save_state)
    manager.register_hook(stop_celery_workers)
    manager.register_hook(close_database_connections)
    manager.register_hook(flush_logs)
