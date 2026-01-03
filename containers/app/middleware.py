#!/usr/bin/env python3
"""
FastAPI Middleware for IPAM4Cloud

This module contains middleware for handling cross-cutting concerns like:
- Request ID tracking and propagation
- Request/response logging
- Performance monitoring
"""

import uuid
import time
import json
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle X-Request-ID headers for request tracking.
    
    Features:
    - Extracts X-Request-ID from incoming requests
    - Generates UUID if no request ID provided
    - Adds request ID to response headers
    - Makes request ID available to endpoints via request.state
    """
    
    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Request-ID",
        generate_if_missing: bool = True
    ):
        super().__init__(app)
        self.header_name = header_name
        self.generate_if_missing = generate_if_missing
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract request ID from header
        request_id = request.headers.get(self.header_name)
        
        # Generate UUID if missing and generation is enabled
        if not request_id and self.generate_if_missing:
            request_id = str(uuid.uuid4())
        
        # Store request ID in request state for access by endpoints
        request.state.request_id = request_id
        
        # Process the request
        response = await call_next(request)
        
        # Add request ID to response headers
        if request_id:
            response.headers[self.header_name] = request_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging API requests and responses.
    
    Features:
    - Logs request method, path, and request ID
    - Logs response status and processing time
    - Optionally logs request/response bodies
    - Structured logging for easy parsing
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_request_body: bool = False,
        log_response_body: bool = False,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        start_time = time.time()
        request_id = getattr(request.state, 'request_id', None)
        
        # Log request
        log_data = {
            'event': 'request_start',
            'method': request.method,
            'path': request.url.path,
            'query_params': str(request.query_params),
            'request_id': request_id,
            'client_ip': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent')
        }
        
        # Optionally log request body
        if self.log_request_body and request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = await request.body()
                if body:
                    log_data['request_body'] = body.decode('utf-8')
            except Exception as e:
                log_data['request_body_error'] = str(e)
        
        logger.info("API Request", extra=log_data)
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log response
        log_data = {
            'event': 'request_complete',
            'method': request.method,
            'path': request.url.path,
            'request_id': request_id,
            'status_code': response.status_code,
            'processing_time_ms': round(processing_time * 1000, 2)
        }
        
        # Optionally log response body
        if self.log_response_body and hasattr(response, 'body'):
            try:
                log_data['response_body'] = response.body.decode('utf-8')
            except Exception as e:
                log_data['response_body_error'] = str(e)
        
        logger.info("API Response", extra=log_data)
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for consistent error handling and response formatting.
    
    Features:
    - Catches unhandled exceptions
    - Returns consistent error response format
    - Includes request ID in error responses
    - Logs errors with context
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            # Let FastAPI handle HTTPException (e.g., 409 Conflict, 400 Bad Request)
            # FastAPI will automatically convert it to the appropriate HTTP response
            raise
        except Exception as e:
            request_id = getattr(request.state, 'request_id', None)
            
            # Log the error
            logger.error(
                f"Unhandled exception in {request.method} {request.url.path}",
                extra={
                    'request_id': request_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'method': request.method,
                    'path': request.url.path
                },
                exc_info=True
            )
            
            # Return consistent error response
            error_response = {
                'error': 'internal_server_error',
                'message': 'An internal server error occurred',
                'request_id': request_id,
                'timestamp': time.time()
            }
            
            return JSONResponse(
                status_code=500,
                content=error_response,
                headers={'X-Request-ID': request_id} if request_id else {}
            )


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for monitoring API performance.
    
    Features:
    - Tracks request processing times
    - Monitors slow requests
    - Collects endpoint usage statistics
    - Can be extended to integrate with monitoring systems
    """
    
    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold_ms: float = 1000.0,
        collect_stats: bool = True
    ):
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms
        self.collect_stats = collect_stats
        self.stats = {}  # In-memory stats (consider using Redis in production)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = getattr(request.state, 'request_id', None)
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Log slow requests
        if processing_time_ms > self.slow_request_threshold_ms:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path}",
                extra={
                    'request_id': request_id,
                    'processing_time_ms': processing_time_ms,
                    'threshold_ms': self.slow_request_threshold_ms,
                    'method': request.method,
                    'path': request.url.path,
                    'status_code': response.status_code
                }
            )
        
        # Collect statistics
        if self.collect_stats:
            endpoint_key = f"{request.method} {request.url.path}"
            if endpoint_key not in self.stats:
                self.stats[endpoint_key] = {
                    'count': 0,
                    'total_time_ms': 0,
                    'min_time_ms': float('inf'),
                    'max_time_ms': 0,
                    'status_codes': {}
                }
            
            stats = self.stats[endpoint_key]
            stats['count'] += 1
            stats['total_time_ms'] += processing_time_ms
            stats['min_time_ms'] = min(stats['min_time_ms'], processing_time_ms)
            stats['max_time_ms'] = max(stats['max_time_ms'], processing_time_ms)
            
            status_code = str(response.status_code)
            stats['status_codes'][status_code] = stats['status_codes'].get(status_code, 0) + 1
        
        # Add performance headers
        response.headers['X-Processing-Time-MS'] = str(round(processing_time_ms, 2))
        
        return response
    
    def get_stats(self) -> dict:
        """Get collected performance statistics"""
        # Calculate averages
        result = {}
        for endpoint, stats in self.stats.items():
            if stats['count'] > 0:
                result[endpoint] = {
                    'count': stats['count'],
                    'avg_time_ms': round(stats['total_time_ms'] / stats['count'], 2),
                    'min_time_ms': round(stats['min_time_ms'], 2),
                    'max_time_ms': round(stats['max_time_ms'], 2),
                    'status_codes': stats['status_codes']
                }
        return result
    
    def reset_stats(self):
        """Reset collected statistics"""
        self.stats = {}


# Utility functions for middleware setup
def setup_middleware(app, config: Optional[dict] = None):
    """
    Setup all middleware with configuration.
    
    Args:
        app: FastAPI application instance
        config: Optional configuration dictionary
    """
    config = config or {}
    
    # Performance monitoring (should be first to measure total time)
    app.add_middleware(
        PerformanceMonitoringMiddleware,
        slow_request_threshold_ms=config.get('slow_request_threshold_ms', 1000.0),
        collect_stats=config.get('collect_stats', True)
    )
    
    # Error handling
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Request logging
    app.add_middleware(
        RequestLoggingMiddleware,
        log_request_body=config.get('log_request_body', False),
        log_response_body=config.get('log_response_body', False),
        exclude_paths=config.get('exclude_paths', ["/health", "/metrics"])
    )
    
    # Request ID tracking (should be last to ensure it's available to all other middleware)
    app.add_middleware(
        RequestIDMiddleware,
        header_name=config.get('request_id_header', "X-Request-ID"),
        generate_if_missing=config.get('generate_request_id', True)
    )


