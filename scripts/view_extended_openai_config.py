#!/usr/bin/env python3
"""
Extended OpenAI Conversation - Configuration Helper

This script helps you view and extract the Extended OpenAI Conversation
configuration from Home Assistant's storage files.
"""

import json
import sys
from pathlib import Path

# Path to Home Assistant config
HA_CONFIG = Path("/home/user/LCARS-at-Home/docker/volumes/homeassistant")
STORAGE_FILE = HA_CONFIG / ".storage" / "core.config_entries"

def find_extended_openai_config():
    """Find Extended OpenAI Conversation configuration."""
    if not STORAGE_FILE.exists():
        print(f"❌ Storage file not found: {STORAGE_FILE}")
        print("   Home Assistant may not be initialized yet.")
        return None

    try:
        with open(STORAGE_FILE, 'r') as f:
            data = json.load(f)

        # Find Extended OpenAI entry
        entries = data.get('data', {}).get('entries', [])
        extended_openai = next(
            (e for e in entries if e.get('domain') == 'extended_openai_conversation'),
            None
        )

        if not extended_openai:
            print("❌ Extended OpenAI Conversation integration not found")
            print("   It may not be installed yet.")
            return None

        return extended_openai

    except json.JSONDecodeError as e:
        print(f"❌ Error reading storage file: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def display_config(config):
    """Display the configuration in a readable format."""
    print("=" * 80)
    print("Extended OpenAI Conversation Configuration")
    print("=" * 80)

    # Basic info
    print(f"\nEntry ID: {config.get('entry_id')}")
    print(f"Domain: {config.get('domain')}")
    print(f"Version: {config.get('version')}")

    # Connection data
    data = config.get('data', {})
    print("\n--- Connection Settings ---")
    print(f"API Base: {data.get('api_base', 'not set')}")
    print(f"Model: {data.get('model', 'not set')}")
    print(f"API Key: {'***' if data.get('api_key') else 'not set'}")

    # Options
    options = config.get('options', {})
    print("\n--- Model Settings ---")
    print(f"Max Tokens: {options.get('max_tokens', 'default')}")
    print(f"Temperature: {options.get('temperature', 'default')}")
    print(f"Top P: {options.get('top_p', 'default')}")

    # Functions
    functions = options.get('functions', '')
    if functions:
        # Count function definitions
        func_count = functions.count('- spec:')
        print(f"\n--- Functions ---")
        print(f"Total functions defined: {func_count}")

        # Extract function names
        import re
        names = re.findall(r'name:\s*(\w+)', functions)
        if names:
            print("Function names:")
            for i, name in enumerate(names, 1):
                print(f"  {i}. {name}")
    else:
        print("\n--- Functions ---")
        print("No functions defined")

    # System prompt
    prompt = options.get('prompt', '')
    if prompt:
        print(f"\n--- System Prompt ---")
        print(f"Length: {len(prompt)} characters")
        print(f"Preview: {prompt[:100]}...")

    print("\n" + "=" * 80)


def extract_functions_yaml(config):
    """Extract the functions YAML spec."""
    options = config.get('options', {})
    functions = options.get('functions', '')

    if not functions:
        print("No functions spec found in configuration")
        return

    print("\n--- Functions YAML Spec ---")
    print("Copy this to update your configuration:")
    print("\n" + functions)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="View Extended OpenAI Conversation configuration"
    )
    parser.add_argument(
        '--extract-functions',
        action='store_true',
        help="Extract and display the functions YAML spec"
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help="Output raw JSON configuration"
    )

    args = parser.parse_args()

    # Find config
    config = find_extended_openai_config()
    if not config:
        sys.exit(1)

    # Display based on options
    if args.json:
        print(json.dumps(config, indent=2))
    elif args.extract_functions:
        extract_functions_yaml(config)
    else:
        display_config(config)


if __name__ == '__main__':
    main()
