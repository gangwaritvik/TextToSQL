"""
Test script to check how tokens are returned from Azure OpenAI
"""
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment
load_dotenv(".env.local")

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.config.llm import model

# Test a simple query
response = model.invoke("What is 2+2?")

print("=" * 80)
print("RESPONSE OBJECT TYPE:", type(response))
print("=" * 80)
print("\nFull Response:")
print(response)
print("\n" + "=" * 80)
print("Response Attributes:")
print("=" * 80)
print(dir(response))
print("\n" + "=" * 80)
print("Response Content:", response.content)
print("\n" + "=" * 80)

# Check for usage/tokens
if hasattr(response, 'usage'):
    print("✓ Has usage attribute:", response.usage)
else:
    print("✗ No usage attribute")

if hasattr(response, 'response_metadata'):
    print("✓ Has response_metadata:", response.response_metadata)
else:
    print("✗ No response_metadata")

if hasattr(response, 'usage_metadata'):
    print("✓ Has usage_metadata:", response.usage_metadata)
else:
    print("✗ No usage_metadata")

print("\n" + "=" * 80)
