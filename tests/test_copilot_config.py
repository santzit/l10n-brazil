#!/usr/bin/env python3
"""
Simple validation script for GitHub Copilot configuration files.
This ensures all JSON files are properly formatted and contain expected keys.
"""

import json
import os
import sys


def test_json_file(filepath, expected_keys=None):
    """Test if a JSON file is valid and contains expected keys."""
    try:
        print(f"Testing {filepath}...")
        
        if not os.path.exists(filepath):
            print(f"❌ File does not exist: {filepath}")
            return False
            
        with open(filepath) as f:
            data = json.load(f)
            
        print(f"✅ Valid JSON: {filepath}")
        
        if expected_keys:
            for key in expected_keys:
                if key not in data:
                    print(f"❌ Missing expected key '{key}' in {filepath}")
                    return False
                print(f"✅ Found expected key '{key}' in {filepath}")
                
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {filepath}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing {filepath}: {e}")
        return False

def test_file_exists(filepath):
    """Test if a file exists."""
    if os.path.exists(filepath):
        print(f"✅ File exists: {filepath}")
        return True
    else:
        print(f"❌ File missing: {filepath}")
        return False

def main():
    """Run all configuration tests."""
    print("🚀 Testing GitHub Copilot configuration files...\n")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)  # Go up from tests/ to project root
    
    tests = [
        # Test JSON files
        (lambda: test_json_file(
            os.path.join(project_root, ".github", "mcp-server-config.json"),
            ["repositories", "context", "instructions"]
        )),
        (lambda: test_json_file(
            os.path.join(project_root, ".vscode", "settings.json"),
            ["github.copilot.enable"]
        )),
        (lambda: test_json_file(
            os.path.join(project_root, "l10n-brazil-odoo.code-workspace"),
            ["folders", "settings"]
        )),
        
        # Test markdown files exist
        (lambda: test_file_exists(
            os.path.join(project_root, ".github", "copilot-instructions.md")
        )),
        (lambda: test_file_exists(
            os.path.join(project_root, "docs", "copilot-setup.md")
        )),
        (lambda: test_file_exists(
            os.path.join(project_root, "docs", "copilot-quick-reference.md")
        )),
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Empty line between tests
    
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All GitHub Copilot configuration tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Please check the configuration files.")
        return 1

if __name__ == "__main__":
    sys.exit(main())