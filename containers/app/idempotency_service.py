#!/usr/bin/env python3
"""
Idempotency Service for IPAM4Cloud API

This service implements idempotent request handling to prevent duplicate operations.
When a request includes a request_id:
- If it's new, we process the request and store the result
- If it exists with matching parameters, we return the cached result
- If it exists with different parameters, we return an error

Features:
- Automatic UUID generation for requests without request_id
- Parameter hashing for efficient comparison
- Permanent idempotency records (no expiration)
- Thread-safe operations
"""

import uuid
import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from models import IdempotencyRecord, DatabaseManager


class IdempotencyError(Exception):
    """Custom exception for idempotency-related errors"""
    pass


class ParameterMismatchError(IdempotencyError):
    """Raised when request_id exists but parameters don't match"""
    pass


class IdempotencyService:
    """
    Service for handling idempotent API requests
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def generate_request_id(self) -> str:
        """Generate a new UUID for requests without request_id"""
        return str(uuid.uuid4())
    
    def _calculate_request_hash(self, params: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of request parameters for comparison"""
        # Remove request_id from params before hashing to avoid circular dependency
        clean_params = {k: v for k, v in params.items() if k != 'request_id'}
        
        # Sort parameters to ensure consistent hashing
        sorted_params = json.dumps(clean_params, sort_keys=True, default=str)
        return hashlib.sha256(sorted_params.encode()).hexdigest()
    
    def _serialize_for_storage(self, data: Any) -> Dict[str, Any]:
        """Serialize data for JSON storage, handling special types including datetime"""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {k: self._serialize_for_storage(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_for_storage(item) for item in data]
        elif hasattr(data, 'dict'):  # Pydantic model
            return self._serialize_for_storage(data.dict())
        elif hasattr(data, '__dict__'):  # Regular object
            return self._serialize_for_storage({k: v for k, v in data.__dict__.items() if not k.startswith('_')})
        else:
            return data
    
    def check_idempotency(
        self,
        request_id: str,
        endpoint: str,
        method: str,
        request_params: Dict[str, Any]
    ) -> Optional[Tuple[Dict[str, Any], int]]:
        """
        Check if request is idempotent and return cached result if available.
        
        Args:
            request_id: Unique identifier for the request
            endpoint: API endpoint path
            method: HTTP method
            request_params: Request parameters to compare
            
        Returns:
            Tuple of (response_data, status_code) if cached result exists, None otherwise
            
        Raises:
            ParameterMismatchError: If request_id exists but parameters don't match
        """
        session = self.db_manager.get_session()
        try:
            # Look for existing record
            existing_record = session.query(IdempotencyRecord).filter(
                IdempotencyRecord.request_id == request_id
            ).first()
            
            if not existing_record:
                return None
            
            # Verify endpoint and method match
            if existing_record.endpoint != endpoint or existing_record.method != method:
                raise ParameterMismatchError(
                    f"Request ID {request_id} was previously used for "
                    f"{existing_record.method} {existing_record.endpoint}, "
                    f"but current request is {method} {endpoint}"
                )
            
            # Calculate hash of current parameters
            current_hash = self._calculate_request_hash(request_params)
            
            # Compare parameter hashes
            if existing_record.request_hash != current_hash:
                # Parameters don't match - this is an error
                raise ParameterMismatchError(
                    f"Request ID {request_id} was previously used with different parameters. "
                    f"Original request: {existing_record.request_params}. "
                    f"Current request: {request_params}"
                )
            
            # Parameters match - return cached response
            return existing_record.response_data, existing_record.status_code
            
        finally:
            session.close()
    
    def store_response(
        self,
        request_id: str,
        endpoint: str,
        method: str,
        request_params: Dict[str, Any],
        response_data: Any,
        status_code: int
    ) -> None:
        """
        Store the response for future idempotency checks.
        Records are kept permanently and never expire.
        
        Args:
            request_id: Unique identifier for the request
            endpoint: API endpoint path
            method: HTTP method
            request_params: Request parameters
            response_data: Response to cache
            status_code: HTTP status code
        """
        session = self.db_manager.get_session()
        try:
            # Serialize response data
            serialized_response = self._serialize_for_storage(response_data)
            
            # Set expires_at to far future (required by DB schema, but not checked)
            expires_at = datetime.now(timezone.utc) + timedelta(days=36500)  # ~100 years
            
            # Create idempotency record
            record = IdempotencyRecord(
                request_id=request_id,
                endpoint=endpoint,
                method=method,
                request_hash=self._calculate_request_hash(request_params),
                request_params=request_params,
                response_data=serialized_response,
                status_code=status_code,
                expires_at=expires_at
            )
            
            session.add(record)
            session.commit()
            
        except IntegrityError:
            # Record already exists (race condition) - this is fine
            session.rollback()
        finally:
            session.close()
    
    def get_record_stats(self) -> Dict[str, Any]:
        """
        Get statistics about idempotency records.
        
        Returns:
            Dictionary with record statistics
        """
        session = self.db_manager.get_session()
        try:
            total_records = session.query(IdempotencyRecord).count()
            
            return {
                'total_records': total_records
            }
        finally:
            session.close()


class IdempotencyManager:
    """
    High-level manager for idempotency operations with FastAPI integration
    """
    
    def __init__(self, idempotency_service: IdempotencyService):
        self.service = idempotency_service
    
    def process_request(
        self,
        request_id: Optional[str],
        endpoint: str,
        method: str,
        request_params: Dict[str, Any],
        processor_func,
        *args,
        **kwargs
    ) -> Tuple[Any, int, str]:
        """
        Process a request with idempotency handling.
        
        Args:
            request_id: Optional request ID from client
            endpoint: API endpoint path
            method: HTTP method
            request_params: Request parameters
            processor_func: Function to call if request needs processing
            *args, **kwargs: Arguments to pass to processor_func
            
        Returns:
            Tuple of (response_data, status_code, actual_request_id)
        """
        # Generate request ID if not provided
        if not request_id:
            request_id = self.service.generate_request_id()
        
        try:
            # Check for existing idempotent response
            cached_result = self.service.check_idempotency(
                request_id, endpoint, method, request_params
            )
            
            if cached_result:
                response_data, status_code = cached_result
                return response_data, status_code, request_id
            
            # Process new request
            response_data = processor_func(*args, **kwargs)
            status_code = 200  # Default success status
            
            # Store response for future idempotency
            self.service.store_response(
                request_id, endpoint, method, request_params,
                response_data, status_code
            )
            
            return response_data, status_code, request_id
            
        except ParameterMismatchError as e:
            raise HTTPException(
                status_code=409,  # Conflict
                detail={
                    'error': 'parameter_mismatch',
                    'message': str(e),
                    'request_id': request_id
                }
            )
        except HTTPException:
            # Let HTTPException propagate (e.g., from processor_func)
            raise
        except Exception as e:
            # Don't store failed requests in idempotency cache
            raise e


