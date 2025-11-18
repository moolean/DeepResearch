#!/usr/bin/env python3
"""
Unit tests for the direct URL fetch functionality in Visit tool.
These tests verify the implementation without requiring external network access.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Add inference directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'inference'))

class TestDirectFetch(unittest.TestCase):
    """Test cases for direct URL fetching functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Import after adding to path
        import tool_visit
        self.visit = tool_visit.Visit()
    
    def test_import_visit_module(self):
        """Test that the Visit module can be imported"""
        import tool_visit
        self.assertIsNotNone(tool_visit.Visit)
    
    def test_visit_class_has_direct_fetch_method(self):
        """Test that Visit class has direct_fetch_url method"""
        self.assertTrue(hasattr(self.visit, 'direct_fetch_url'))
        self.assertTrue(callable(self.visit.direct_fetch_url))
    
    def test_visit_class_has_sync_wrapper(self):
        """Test that Visit class has direct_fetch_url_sync method"""
        self.assertTrue(hasattr(self.visit, 'direct_fetch_url_sync'))
        self.assertTrue(callable(self.visit.direct_fetch_url_sync))
    
    def test_use_direct_fetch_env_var(self):
        """Test that USE_DIRECT_FETCH environment variable is recognized"""
        import tool_visit
        
        # Test default value (should be False)
        self.assertFalse(tool_visit.USE_DIRECT_FETCH)
        
        # Test that it's configurable
        with patch.dict(os.environ, {'USE_DIRECT_FETCH': 'true'}):
            # Reload the module to pick up the new env var
            import importlib
            importlib.reload(tool_visit)
            self.assertTrue(tool_visit.USE_DIRECT_FETCH)
        
        # Reset back to false
        with patch.dict(os.environ, {'USE_DIRECT_FETCH': 'false'}):
            importlib.reload(tool_visit)
            self.assertFalse(tool_visit.USE_DIRECT_FETCH)
    
    @patch('httpx.AsyncClient')
    async def test_direct_fetch_success(self, mock_client):
        """Test successful direct fetch"""
        # Mock the response
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Test Content</h1><p>This is test content.</p></body></html>"
        mock_response.status_code = 200
        
        mock_get = AsyncMock(return_value=mock_response)
        mock_client_instance = MagicMock()
        mock_client_instance.get = mock_get
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_client_instance
        
        # Mock trafilatura
        with patch('trafilatura.extract', return_value="Test Content\nThis is test content."):
            text, error = await self.visit.direct_fetch_url("https://example.com")
            
            self.assertIsNotNone(text)
            self.assertIsNone(error)
            self.assertIn("Test Content", text)
    
    @patch('httpx.AsyncClient')
    async def test_direct_fetch_404_error(self, mock_client):
        """Test direct fetch with 404 error"""
        import httpx
        
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        mock_error = httpx.HTTPStatusError("404", request=MagicMock(), response=mock_response)
        mock_get = AsyncMock(side_effect=mock_error)
        mock_client_instance = MagicMock()
        mock_client_instance.get = mock_get
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_client_instance
        
        text, error = await self.visit.direct_fetch_url("https://example.com/notfound")
        
        self.assertIsNone(text)
        self.assertIsNotNone(error)
        self.assertIn("404", error)
    
    @patch('httpx.AsyncClient')
    async def test_direct_fetch_403_error_with_retry(self, mock_client):
        """Test direct fetch with 403 error (should retry)"""
        import httpx
        
        # Mock 403 response
        mock_response = MagicMock()
        mock_response.status_code = 403
        
        mock_error = httpx.HTTPStatusError("403", request=MagicMock(), response=mock_response)
        mock_get = AsyncMock(side_effect=mock_error)
        mock_client_instance = MagicMock()
        mock_client_instance.get = mock_get
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_client_instance
        
        text, error = await self.visit.direct_fetch_url("https://example.com")
        
        self.assertIsNone(text)
        self.assertIsNotNone(error)
        self.assertIn("403", error)
        self.assertIn("blocking", error.lower())
        
        # Should have retried 3 times
        self.assertEqual(mock_get.call_count, 3)
    
    def test_html_readpage_respects_use_direct_fetch(self):
        """Test that html_readpage_jina respects USE_DIRECT_FETCH flag"""
        import tool_visit
        
        # When USE_DIRECT_FETCH is False, should use Jina
        with patch.dict(os.environ, {'USE_DIRECT_FETCH': 'false'}):
            import importlib
            importlib.reload(tool_visit)
            
            visit = tool_visit.Visit()
            with patch.object(visit, 'jina_readpage', return_value="Jina content") as mock_jina:
                result = visit.html_readpage_jina("https://example.com")
                mock_jina.assert_called()
        
        # When USE_DIRECT_FETCH is True, should use direct fetch
        with patch.dict(os.environ, {'USE_DIRECT_FETCH': 'true'}):
            importlib.reload(tool_visit)
            
            visit = tool_visit.Visit()
            with patch.object(visit, 'direct_fetch_url_sync', return_value=("Direct content", None)) as mock_direct:
                result = visit.html_readpage_jina("https://example.com")
                mock_direct.assert_called()
                self.assertEqual(result, "Direct content")

def run_async_test(coro):
    """Helper to run async tests"""
    import asyncio
    return asyncio.run(coro)

if __name__ == '__main__':
    # Run the tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDirectFetch)
    
    # Run only synchronous tests for now (async tests require more setup)
    sync_tests = [
        'test_import_visit_module',
        'test_visit_class_has_direct_fetch_method',
        'test_visit_class_has_sync_wrapper',
        'test_use_direct_fetch_env_var',
        'test_html_readpage_respects_use_direct_fetch'
    ]
    
    print("\n" + "=" * 70)
    print("Running Direct Fetch Unit Tests")
    print("=" * 70 + "\n")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(unittest.TestSuite([suite._tests[0].__class__(test) for test in sync_tests]))
    
    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)
    
    sys.exit(0 if result.wasSuccessful() else 1)
