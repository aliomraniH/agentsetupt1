#!/usr/bin/env python3
"""
API Key Configuration Verification Script

This script verifies that API keys are properly configured for the agent system.
Run this before deployment to catch configuration issues early.

Usage:
    python scripts/verify_api_keys.py
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_environment_variables():
    """Check if API keys exist in environment variables"""
    print("=" * 80)
    print("🔍 ENVIRONMENT VARIABLE CHECK")
    print("=" * 80)

    required_keys = {
        "ANTHROPIC_API_KEY": "Anthropic Claude API",
        "ALPHA_VANTAGE_API_KEY": "Alpha Vantage Stock Data API",
        "PERPLEXITY_API_KEY": "Perplexity AI API"
    }

    results = {}
    all_present = True

    for key, description in required_keys.items():
        value = os.environ.get(key)
        if value and value.strip():
            print(f"✅ {key}: Present ({description})")
            print(f"   Preview: {value[:20]}...{value[-4:]}")
            results[key] = True
        else:
            print(f"❌ {key}: NOT FOUND ({description})")
            results[key] = False
            all_present = False

    return all_present, results


def check_pydantic_settings():
    """Check if pydantic settings are loading API keys correctly"""
    print("\n" + "=" * 80)
    print("⚙️  PYDANTIC SETTINGS CHECK")
    print("=" * 80)

    try:
        from src.core.config import settings

        # Check case sensitivity
        print(f"📋 Config case_sensitive: {settings.Config.case_sensitive}")
        if not settings.Config.case_sensitive:
            print("⚠️  WARNING: case_sensitive is False - may not work with Replit Secrets!")

        # Check if keys are loaded
        keys_status = {
            "anthropic_api_key": settings.anthropic_api_key,
            "alpha_vantage_api_key": settings.alpha_vantage_api_key,
            "perplexity_api_key": settings.perplexity_api_key
        }

        all_loaded = True
        for key, value in keys_status.items():
            if value:
                print(f"✅ settings.{key}: Loaded")
                print(f"   Preview: {value[:20]}...{value[-4:]}")
            else:
                print(f"❌ settings.{key}: NOT LOADED")
                all_loaded = False

        return all_loaded, keys_status

    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        return False, {}


def check_anthropic_client():
    """Check if Anthropic client can be initialized"""
    print("\n" + "=" * 80)
    print("🤖 ANTHROPIC CLIENT CHECK")
    print("=" * 80)

    try:
        from anthropic import Anthropic
        from src.core.config import settings

        if not settings.anthropic_api_key:
            print("❌ Cannot initialize client: API key not loaded in settings")
            return False

        try:
            client = Anthropic(api_key=settings.anthropic_api_key)
            print("✅ Anthropic client initialized successfully")

            # Try a simple API call
            print("\n🧪 Testing API call...")
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            print("✅ API call successful!")
            print(f"   Response: {response.content[0].text}")
            return True

        except Exception as e:
            print(f"❌ Anthropic client error: {e}")
            return False

    except ImportError as e:
        print(f"❌ Anthropic library not installed: {e}")
        return False


def check_replit_environment():
    """Check if running in Replit and provide specific guidance"""
    print("\n" + "=" * 80)
    print("🔧 REPLIT ENVIRONMENT CHECK")
    print("=" * 80)

    is_replit = os.environ.get("REPL_ID") is not None

    if is_replit:
        print("✅ Running in Replit environment")
        print("\n📝 Replit Secrets Configuration:")
        print("   1. Go to Tools > Secrets (or the lock icon)")
        print("   2. Add secrets with EXACT names (case-sensitive):")
        print("      - ANTHROPIC_API_KEY")
        print("      - ALPHA_VANTAGE_API_KEY")
        print("      - PERPLEXITY_API_KEY")
        print("   3. Restart the deployment after adding secrets")
    else:
        print("ℹ️  Not running in Replit")
        print("   Make sure API keys are in environment variables or .env file")

    return is_replit


def generate_report(env_results, settings_results, client_ok):
    """Generate final report with recommendations"""
    print("\n" + "=" * 80)
    print("📊 FINAL REPORT")
    print("=" * 80)

    issues = []

    # Check environment vs settings mismatches
    if env_results and settings_results:
        for key in ["ANTHROPIC_API_KEY", "ALPHA_VANTAGE_API_KEY", "PERPLEXITY_API_KEY"]:
            setting_key = key.lower()
            if env_results.get(key) and not settings_results.get(setting_key):
                issues.append(f"{key} is in environment but NOT loaded by pydantic Settings")

    if issues:
        print("\n⚠️  ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")

        print("\n💡 RECOMMENDED FIXES:")
        print("   1. Ensure src/core/config.py has: case_sensitive = True")
        print("   2. Ensure custom __init__ method with fallback loading is present")
        print("   3. Restart the application after making changes")

    if client_ok:
        print("\n✅ ALL SYSTEMS OPERATIONAL")
        print("   Anthropic API is working correctly!")
    elif not issues:
        print("\n⚠️  Some checks failed but no specific issues detected")
        print("   Review the output above for details")

    return len(issues) == 0 and client_ok


def main():
    """Main verification flow"""
    print("\n" + "🔐" * 40)
    print("API KEY CONFIGURATION VERIFICATION")
    print("🔐" * 40 + "\n")

    # Run all checks
    env_ok, env_results = check_environment_variables()
    settings_ok, settings_results = check_pydantic_settings()
    is_replit = check_replit_environment()
    client_ok = check_anthropic_client()

    # Generate report
    all_ok = generate_report(env_results, settings_results, client_ok)

    # Exit with appropriate code
    if all_ok:
        print("\n✅ Verification PASSED - System ready for deployment")
        sys.exit(0)
    else:
        print("\n❌ Verification FAILED - Fix issues before deployment")
        sys.exit(1)


if __name__ == "__main__":
    main()
