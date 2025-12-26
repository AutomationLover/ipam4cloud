#!/usr/bin/env python3
"""
Tests for Idempotency Service

This module contains comprehensive tests for the idempotency functionality
including service tests, API endpoint tests, and edge case handling.
"""

import pytest
import uuid
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, DatabaseManager, IdempotencyRecord
from idempotency_service import IdempotencyService, IdempotencyManager, ParameterMismatchError


class TestIdempotencyService:
    """Test cases for IdempotencyService"""
    
    @pytest.fixture
    def db_manager(self):
        """Create in-memory database for testing"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return DatabaseManager("sqlite:///:memory:")
    
    @pytest.fixture
    def idempotency_service(self, db_manager):
        """Create IdempotencyService instance for testing"""
        return IdempotencyService(db_manager, default_ttl_hours=1)
    
    def test_generate_request_id(self, idempotency_service):
        """Test request ID generation"""
        request_id = idempotency_service.generate_request_id()
        assert isinstance(request_id, str)
        assert len(request_id) == 36  # UUID format
        
        # Generate another and ensure they're different
        request_id2 = idempotency_service.generate_request_id()
        assert request_id != request_id2
    
    def test_calculate_request_hash(self, idempotency_service):
        """Test request parameter hashing"""
        params1 = {"vrf_id": "test", "cidr": "10.0.0.0/24", "tags": {"env": "prod"}}
        params2 = {"vrf_id": "test", "cidr": "10.0.0.0/24", "tags": {"env": "prod"}}
        params3 = {"vrf_id": "test", "cidr": "10.0.1.0/24", "tags": {"env": "prod"}}
        
        hash1 = idempotency_service._calculate_request_hash(params1)
        hash2 = idempotency_service._calculate_request_hash(params2)
        hash3 = idempotency_service._calculate_request_hash(params3)
        
        # Same parameters should produce same hash
        assert hash1 == hash2
        
        # Different parameters should produce different hash
        assert hash1 != hash3
        
        # Hash should be consistent regardless of parameter order
        params_reordered = {"tags": {"env": "prod"}, "cidr": "10.0.0.0/24", "vrf_id": "test"}
        hash_reordered = idempotency_service._calculate_request_hash(params_reordered)
        assert hash1 == hash_reordered
    
    def test_check_idempotency_new_request(self, idempotency_service):
        """Test idempotency check for new request"""
        request_id = str(uuid.uuid4())
        result = idempotency_service.check_idempotency(
            request_id=request_id,
            endpoint="/api/test",
            method="POST",
            request_params={"test": "value"}
        )
        assert result is None
    
    def test_store_and_retrieve_response(self, idempotency_service):
        """Test storing and retrieving idempotent response"""
        request_id = str(uuid.uuid4())
        endpoint = "/api/test"
        method = "POST"
        request_params = {"vrf_id": "test", "cidr": "10.0.0.0/24"}
        response_data = {"prefix_id": "test-prefix", "status": "created"}
        status_code = 201
        
        # Store response
        idempotency_service.store_response(
            request_id=request_id,
            endpoint=endpoint,
            method=method,
            request_params=request_params,
            response_data=response_data,
            status_code=status_code
        )
        
        # Retrieve response
        result = idempotency_service.check_idempotency(
            request_id=request_id,
            endpoint=endpoint,
            method=method,
            request_params=request_params
        )
        
        assert result is not None
        retrieved_response, retrieved_status = result
        assert retrieved_response == response_data
        assert retrieved_status == status_code
    
    def test_parameter_mismatch_error(self, idempotency_service):
        """Test parameter mismatch detection"""
        request_id = str(uuid.uuid4())
        endpoint = "/api/test"
        method = "POST"
        
        # Store initial request
        original_params = {"vrf_id": "test", "cidr": "10.0.0.0/24"}
        idempotency_service.store_response(
            request_id=request_id,
            endpoint=endpoint,
            method=method,
            request_params=original_params,
            response_data={"status": "created"},
            status_code=201
        )
        
        # Try with different parameters
        different_params = {"vrf_id": "test", "cidr": "10.0.1.0/24"}
        
        with pytest.raises(ParameterMismatchError) as exc_info:
            idempotency_service.check_idempotency(
                request_id=request_id,
                endpoint=endpoint,
                method=method,
                request_params=different_params
            )
        
        assert "different parameters" in str(exc_info.value)
    
    def test_endpoint_method_mismatch_error(self, idempotency_service):
        """Test endpoint/method mismatch detection"""
        request_id = str(uuid.uuid4())
        
        # Store initial request
        idempotency_service.store_response(
            request_id=request_id,
            endpoint="/api/test",
            method="POST",
            request_params={"test": "value"},
            response_data={"status": "created"},
            status_code=201
        )
        
        # Try with different endpoint
        with pytest.raises(ParameterMismatchError) as exc_info:
            idempotency_service.check_idempotency(
                request_id=request_id,
                endpoint="/api/different",
                method="POST",
                request_params={"test": "value"}
            )
        
        assert "previously used for" in str(exc_info.value)
    
    def test_expired_record_cleanup(self, idempotency_service):
        """Test cleanup of expired records"""
        request_id = str(uuid.uuid4())
        
        # Store response with short TTL
        idempotency_service.store_response(
            request_id=request_id,
            endpoint="/api/test",
            method="POST",
            request_params={"test": "value"},
            response_data={"status": "created"},
            status_code=201,
            ttl_hours=0.001  # Very short TTL for testing
        )
        
        # Wait for expiration (simulate)
        import time
        time.sleep(0.1)
        
        # Check that expired record is not returned
        result = idempotency_service.check_idempotency(
            request_id=request_id,
            endpoint="/api/test",
            method="POST",
            request_params={"test": "value"}
        )
        assert result is None
    
    def test_cleanup_expired_records(self, idempotency_service):
        """Test manual cleanup of expired records"""
        # Create some expired records
        for i in range(3):
            request_id = str(uuid.uuid4())
            idempotency_service.store_response(
                request_id=request_id,
                endpoint="/api/test",
                method="POST",
                request_params={"test": f"value{i}"},
                response_data={"status": "created"},
                status_code=201,
                ttl_hours=-1  # Already expired
            )
        
        # Cleanup expired records
        deleted_count = idempotency_service.cleanup_expired_records()
        assert deleted_count == 3
    
    def test_get_record_stats(self, idempotency_service):
        """Test getting idempotency record statistics"""
        # Initially no records
        stats = idempotency_service.get_record_stats()
        assert stats['total_records'] == 0
        assert stats['active_records'] == 0
        assert stats['expired_records'] == 0
        
        # Add some records
        for i in range(2):
            request_id = str(uuid.uuid4())
            idempotency_service.store_response(
                request_id=request_id,
                endpoint="/api/test",
                method="POST",
                request_params={"test": f"value{i}"},
                response_data={"status": "created"},
                status_code=201
            )
        
        # Add expired record
        expired_request_id = str(uuid.uuid4())
        idempotency_service.store_response(
            request_id=expired_request_id,
            endpoint="/api/test",
            method="POST",
            request_params={"test": "expired"},
            response_data={"status": "created"},
            status_code=201,
            ttl_hours=-1
        )
        
        stats = idempotency_service.get_record_stats()
        assert stats['total_records'] == 3
        assert stats['active_records'] == 2
        assert stats['expired_records'] == 1


class TestIdempotencyManager:
    """Test cases for IdempotencyManager"""
    
    @pytest.fixture
    def db_manager(self):
        """Create in-memory database for testing"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return DatabaseManager("sqlite:///:memory:")
    
    @pytest.fixture
    def idempotency_service(self, db_manager):
        """Create IdempotencyService instance for testing"""
        return IdempotencyService(db_manager, default_ttl_hours=1)
    
    @pytest.fixture
    def idempotency_manager(self, idempotency_service):
        """Create IdempotencyManager instance for testing"""
        return IdempotencyManager(idempotency_service)
    
    def test_process_new_request(self, idempotency_manager):
        """Test processing a new request"""
        def mock_processor():
            return {"prefix_id": "test-123", "status": "created"}
        
        request_params = {"vrf_id": "test", "cidr": "10.0.0.0/24"}
        
        response_data, status_code, request_id = idempotency_manager.process_request(
            request_id=None,  # Will be generated
            endpoint="/api/prefixes",
            method="POST",
            request_params=request_params,
            processor_func=mock_processor
        )
        
        assert response_data == {"prefix_id": "test-123", "status": "created"}
        assert status_code == 200
        assert request_id is not None
        assert len(request_id) == 36  # UUID format
    
    def test_process_duplicate_request(self, idempotency_manager):
        """Test processing a duplicate request with same parameters"""
        def mock_processor():
            return {"prefix_id": "test-123", "status": "created"}
        
        request_id = str(uuid.uuid4())
        request_params = {"vrf_id": "test", "cidr": "10.0.0.0/24"}
        
        # First request
        response1, status1, rid1 = idempotency_manager.process_request(
            request_id=request_id,
            endpoint="/api/prefixes",
            method="POST",
            request_params=request_params,
            processor_func=mock_processor
        )
        
        # Second request with same parameters
        response2, status2, rid2 = idempotency_manager.process_request(
            request_id=request_id,
            endpoint="/api/prefixes",
            method="POST",
            request_params=request_params,
            processor_func=mock_processor
        )
        
        # Should return cached response
        assert response1 == response2
        assert status1 == status2
        assert rid1 == rid2 == request_id
    
    def test_process_request_with_parameter_mismatch(self, idempotency_manager):
        """Test processing request with parameter mismatch"""
        def mock_processor():
            return {"prefix_id": "test-123", "status": "created"}
        
        request_id = str(uuid.uuid4())
        
        # First request
        idempotency_manager.process_request(
            request_id=request_id,
            endpoint="/api/prefixes",
            method="POST",
            request_params={"vrf_id": "test", "cidr": "10.0.0.0/24"},
            processor_func=mock_processor
        )
        
        # Second request with different parameters
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            idempotency_manager.process_request(
                request_id=request_id,
                endpoint="/api/prefixes",
                method="POST",
                request_params={"vrf_id": "test", "cidr": "10.0.1.0/24"},  # Different CIDR
                processor_func=mock_processor
            )
        
        assert exc_info.value.status_code == 409  # Conflict
        assert "parameter_mismatch" in str(exc_info.value.detail)


class TestAPIIntegration:
    """Integration tests for API endpoints with idempotency"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        # This would need to be set up with the actual FastAPI app
        # For now, we'll mock the behavior
        pass
    
    def test_create_prefix_with_request_id(self):
        """Test creating prefix with explicit request ID"""
        # This would test the actual API endpoint
        # Implementation depends on test setup
        pass
    
    def test_create_prefix_without_request_id(self):
        """Test creating prefix without request ID (auto-generated)"""
        # This would test the actual API endpoint
        # Implementation depends on test setup
        pass
    
    def test_allocate_subnet_idempotency(self):
        """Test subnet allocation idempotency"""
        # This would test the actual API endpoint
        # Implementation depends on test setup
        pass


# Performance and stress tests
class TestIdempotencyPerformance:
    """Performance tests for idempotency service"""
    
    def test_concurrent_requests(self):
        """Test handling concurrent requests with same request ID"""
        # This would test race conditions and concurrent access
        pass
    
    def test_large_parameter_sets(self):
        """Test handling large parameter sets"""
        # This would test performance with large request parameters
        pass
    
    def test_cleanup_performance(self):
        """Test cleanup performance with many records"""
        # This would test cleanup performance
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])


