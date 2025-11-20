#!/usr/bin/env python3
"""
Test script for Visit tool enhancements:
1. Direct URL fetching (USE_DIRECT_FETCH)
2. No-summary mode (ENABLE_SUMMARY)
3. Tool response omission (OMIT_TOOL_RESPONSE_ROUNDS)
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'inference'))

from tool_visit import Visit
from react_agent import MultiTurnReactAgent


class TestDirectFetch(unittest.TestCase):
    """Test direct URL fetching functionality"""
    
    def setUp(self):
        self.visit_tool = Visit()
    
    @patch.dict(os.environ, {'USE_DIRECT_FETCH': 'true'})
    def test_direct_fetch_enabled(self):
        """Test that direct fetch is used when USE_DIRECT_FETCH is true"""
        from tool_visit import USE_DIRECT_FETCH
        # Reload module to pick up env var
        import importlib
        import tool_visit
        importlib.reload(tool_visit)
        
        visit_tool = tool_visit.Visit()
        
        # Test with a simple URL
        url = "https://example.com"
        content = visit_tool.direct_fetch_url(url, max_retries=1)
        
        # Should either succeed or return error message
        self.assertIsInstance(content, str)
        print(f"✓ Direct fetch result type: {type(content)}")
        print(f"  Content length: {len(content)}")
        
    def test_remove_text_links(self):
        """Test markdown link removal"""
        text = "Check out [this link](https://example.com) and [another](https://test.com)"
        expected = "Check out this link and another"
        result = self.visit_tool.remove_text_links(text)
        self.assertEqual(result, expected)
        print("✓ Markdown link removal works correctly")
    
    def test_get_domain(self):
        """Test domain extraction"""
        url = "https://www.example.com/path/to/page?query=1"
        domain = self.visit_tool.get_domain(url)
        self.assertEqual(domain, "www.example.com")
        print(f"✓ Domain extraction works: {domain}")


class TestNoSummaryMode(unittest.TestCase):
    """Test no-summary mode functionality"""
    
    @patch.dict(os.environ, {'ENABLE_SUMMARY': 'false', 'USE_DIRECT_FETCH': 'false'})
    def test_no_summary_mode(self):
        """Test that content is returned without summarization when ENABLE_SUMMARY is false"""
        # Reload module to pick up env var
        import importlib
        import tool_visit
        importlib.reload(tool_visit)
        
        visit_tool = tool_visit.Visit()
        
        # Mock the html_readpage_jina to return test content
        test_content = "This is test webpage content with some information."
        with patch.object(visit_tool, 'html_readpage_jina', return_value=test_content):
            result = visit_tool.readpage_jina("https://example.com", "test goal")
            
            # Should contain the content without summary model processing
            self.assertIn("test goal", result)
            self.assertIn("[Content]:", result)
            self.assertIn("[URL]:", result)
            self.assertIn("[Website]:", result)
            self.assertIn(test_content, result)
            
            # Should NOT contain "Evidence in page" which is from summary model
            self.assertNotIn("Evidence in page:", result)
            
            print("✓ No-summary mode works correctly")
            print(f"  Result format validated")
    
    @patch.dict(os.environ, {'ENABLE_SUMMARY': 'true'})
    def test_summary_mode_enabled(self):
        """Test that summary model is used when ENABLE_SUMMARY is true"""
        # Reload module to pick up env var
        import importlib
        import tool_visit
        importlib.reload(tool_visit)
        
        visit_tool = tool_visit.Visit()
        
        # Mock the html_readpage_jina and call_server
        test_content = "This is test webpage content."
        test_summary = '{"evidence": "Test evidence", "summary": "Test summary"}'
        
        with patch.object(visit_tool, 'html_readpage_jina', return_value=test_content):
            with patch.object(visit_tool, 'call_server', return_value=test_summary):
                result = visit_tool.readpage_jina("https://example.com", "test goal")
                
                # Should contain summary model output
                self.assertIn("Evidence in page:", result)
                self.assertIn("Summary:", result)
                
                print("✓ Summary mode works correctly")


class TestToolResponseOmission(unittest.TestCase):
    """Test tool response omission functionality"""
    
    def test_omit_old_tool_responses(self):
        """Test that old tool responses are omitted correctly"""
        # Create a mock agent with minimal setup
        llm_config = {
            "model_path": "/tmp/mock_model",
            "generate_cfg": {"temperature": 0.7}
        }
        
        # Mock AutoTokenizer to avoid model loading
        with patch('react_agent.AutoTokenizer') as mock_tokenizer:
            mock_tokenizer.from_pretrained.return_value = MagicMock()
            
            # Create agent instance
            agent = MultiTurnReactAgent(llm=llm_config)
            
            # Create test messages with multiple tool responses
            messages = [
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "Question"},
                {"role": "assistant", "content": "Answer 1"},
                {"role": "tool", "tool_call_id": "1", "name": "search", "content": "<tool_response>\nOld response 1\n</tool_response>"},
                {"role": "assistant", "content": "Answer 2"},
                {"role": "tool", "tool_call_id": "2", "name": "visit", "content": "<tool_response>\nOld response 2\n</tool_response>"},
                {"role": "assistant", "content": "Answer 3"},
                {"role": "tool", "tool_call_id": "3", "name": "search", "content": "<tool_response>\nRecent response 1\n</tool_response>"},
                {"role": "assistant", "content": "Answer 4"},
                {"role": "tool", "tool_call_id": "4", "name": "visit", "content": "<tool_response>\nRecent response 2\n</tool_response>"},
            ]
            
            # Keep only last 2 rounds
            result = agent.omit_old_tool_responses(messages, keep_rounds=2)
            
            # Check that old responses are omitted
            self.assertIn("tool response omitted", result[3]["content"])
            self.assertIn("tool response omitted", result[5]["content"])
            
            # Check that recent responses are kept
            self.assertIn("Recent response 1", result[7]["content"])
            self.assertIn("Recent response 2", result[9]["content"])
            
            print("✓ Tool response omission works correctly")
            print(f"  Old responses omitted: 2")
            print(f"  Recent responses kept: 2")
    
    def test_omit_disabled(self):
        """Test that omission is disabled when keep_rounds is 0"""
        llm_config = {
            "model_path": "/tmp/mock_model",
            "generate_cfg": {"temperature": 0.7}
        }
        
        with patch('react_agent.AutoTokenizer') as mock_tokenizer:
            mock_tokenizer.from_pretrained.return_value = MagicMock()
            
            agent = MultiTurnReactAgent(llm=llm_config)
            
            messages = [
                {"role": "tool", "tool_call_id": "1", "content": "<tool_response>\nTest\n</tool_response>"}
            ]
            
            result = agent.omit_old_tool_responses(messages, keep_rounds=0)
            
            # Should return messages unchanged
            self.assertEqual(result, messages)
            print("✓ Omission correctly disabled when keep_rounds=0")


class TestIntegration(unittest.TestCase):
    """Integration tests for all enhancements"""
    
    @patch.dict(os.environ, {'USE_DIRECT_FETCH': 'true', 'ENABLE_SUMMARY': 'false'})
    def test_direct_fetch_without_summary(self):
        """Test direct fetch with no-summary mode"""
        import importlib
        import tool_visit
        importlib.reload(tool_visit)
        
        visit_tool = tool_visit.Visit()
        
        # Mock direct fetch to return test content
        test_content = "Example Domain\nThis domain is for use in illustrative examples."
        with patch.object(visit_tool, 'direct_fetch_url', return_value=test_content):
            result = visit_tool.readpage_jina("https://example.com", "test goal")
            
            # Should use direct fetch and return content without summary
            self.assertIn("Example Domain", result)
            self.assertIn("[Content]:", result)
            self.assertNotIn("Evidence in page:", result)
            
            print("✓ Direct fetch + no-summary integration works")


def run_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("Testing Visit Tool Enhancements")
    print("="*70)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDirectFetch))
    suite.addTests(loader.loadTestsFromTestCase(TestNoSummaryMode))
    suite.addTests(loader.loadTestsFromTestCase(TestToolResponseOmission))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
