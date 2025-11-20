#!/usr/bin/env python3
"""
Tests to verify the correct separation of visit, fetch_url, and browse tools.
"""
import os
import sys

# Add inference directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'inference'))

from tool_visit import Visit
from tool_fetch_url import FetchUrl
from tool_browse import Browse


def test_tool_separation():
    """Test that the three tools have different parameter requirements"""
    print("\n=== Testing Tool Separation ===")
    
    visit = Visit()
    fetch_url = FetchUrl()
    browse = Browse()
    
    # Visit should require both url and goal
    assert 'url' in visit.parameters['required'], "visit should require url"
    assert 'goal' in visit.parameters['required'], "visit should require goal"
    print("✓ visit requires: url, goal")
    
    # FetchUrl should require only url (no goal)
    assert 'url' in fetch_url.parameters['required'], "fetch_url should require url"
    assert 'goal' not in fetch_url.parameters['properties'], "fetch_url should NOT have goal parameter"
    print("✓ fetch_url requires: url (no goal)")
    
    # Browse should require only query (no url or goal)
    assert 'query' in browse.parameters['required'], "browse should require query"
    assert 'url' not in browse.parameters['properties'], "browse should NOT have url parameter"
    assert 'goal' not in browse.parameters['properties'], "browse should NOT have goal parameter"
    print("✓ browse requires: query (no url or goal)")
    
    print("✓ All three tools have correct parameter separation")
    return True


def test_tool_descriptions():
    """Test that the three tools have appropriate descriptions"""
    print("\n=== Testing Tool Descriptions ===")
    
    visit = Visit()
    fetch_url = FetchUrl()
    browse = Browse()
    
    # Check descriptions exist and are different
    assert visit.description != fetch_url.description, \
        "visit and fetch_url should have different descriptions"
    assert visit.description != browse.description, \
        "visit and browse should have different descriptions"
    assert fetch_url.description != browse.description, \
        "fetch_url and browse should have different descriptions"
    
    print(f"✓ visit: {visit.description[:60]}...")
    print(f"✓ fetch_url: {fetch_url.description[:60]}...")
    print(f"✓ browse: {browse.description[:60]}...")
    
    return True


def test_tool_names():
    """Test that the three tools have correct names"""
    print("\n=== Testing Tool Names ===")
    
    visit = Visit()
    fetch_url = FetchUrl()
    browse = Browse()
    
    assert visit.name == 'visit', "visit should have name 'visit'"
    assert fetch_url.name == 'fetch_url', "fetch_url should have name 'fetch_url'"
    assert browse.name == 'browse', "browse should have name 'browse'"
    
    print(f"✓ Tool names are correct: {visit.name}, {fetch_url.name}, {browse.name}")
    
    return True


def test_react_agent_integration():
    """Test that all three tools are available in react_agent"""
    print("\n=== Testing React Agent Integration ===")
    
    import react_agent
    
    # Check that all three tools are in ALL_TOOLS
    assert 'visit' in react_agent.ALL_TOOLS, "visit should be in ALL_TOOLS"
    assert 'fetch_url' in react_agent.ALL_TOOLS, "fetch_url should be in ALL_TOOLS"
    assert 'browse' in react_agent.ALL_TOOLS, "browse should be in ALL_TOOLS"
    
    print(f"✓ All three tools are registered in react_agent.ALL_TOOLS")
    
    # Check that tools are in default enabled tools
    default_tools = react_agent.get_enabled_tools()
    print(f"✓ Default enabled tools: {', '.join(default_tools)}")
    
    return True


def test_prompt_definitions():
    """Test that all three tools have definitions in prompt.py"""
    print("\n=== Testing Prompt Tool Definitions ===")
    
    import prompt
    
    # Check that all three tools have definitions
    assert 'visit' in prompt.TOOL_DEFINITIONS, "visit should have a definition"
    assert 'fetch_url' in prompt.TOOL_DEFINITIONS, "fetch_url should have a definition"
    assert 'browse' in prompt.TOOL_DEFINITIONS, "browse should have a definition"
    
    print(f"✓ All three tools have definitions in TOOL_DEFINITIONS")
    
    return True


def run_all_tests():
    """Run all separation tests"""
    print("="*70)
    print("Testing Tool Separation (visit, fetch_url, browse)")
    print("="*70)
    
    tests = [
        test_tool_names,
        test_tool_separation,
        test_tool_descriptions,
        test_react_agent_integration,
        test_prompt_definitions,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"❌ Test failed: {test.__name__}")
            print(f"   {e}")
            failed += 1
        except Exception as e:
            print(f"❌ Test error: {test.__name__}")
            print(f"   {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70)
    
    if failed == 0:
        print("✅ All tool separation tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
