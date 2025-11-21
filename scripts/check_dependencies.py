#!/usr/bin/env python3
"""
Automatic dependency checker and installer.
Validates requirements.txt compatibility and auto-installs if needed.
"""

import subprocess
import sys
from pathlib import Path


def check_pip_tools():
    """Check if pip-tools is installed for dependency resolution."""
    try:
        import pip_tools
        return True
    except ImportError:
        return False


def install_dependencies(requirements_file: Path):
    """Install dependencies from requirements.txt"""
    print(f"📦 Installing dependencies from {requirements_file}...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies:")
        print(e.stderr)
        return False


def check_conflicts(requirements_file: Path):
    """Check for dependency conflicts using pip check."""
    print("🔍 Checking for dependency conflicts...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ No dependency conflicts detected!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Dependency conflicts detected:")
        print(e.stdout)
        return False


def verify_imports():
    """Verify critical imports work."""
    print("🧪 Verifying critical imports...")

    imports_to_check = [
        ("fastapi", "FastAPI web framework"),
        ("pydantic", "Pydantic validation"),
        ("openai", "OpenAI/Perplexity client"),
        ("yfinance", "Yahoo Finance library"),
        ("loguru", "Loguru logging"),
    ]

    all_ok = True
    for module_name, description in imports_to_check:
        try:
            __import__(module_name)
            print(f"  ✅ {description} ({module_name})")
        except ImportError as e:
            print(f"  ❌ {description} ({module_name}): {e}")
            all_ok = False

    return all_ok


def main():
    """Main dependency checker."""
    print("=" * 60)
    print("🔧 Dependency Checker & Auto-Installer")
    print("=" * 60)

    # Find requirements.txt
    project_root = Path(__file__).parent.parent
    requirements_file = project_root / "requirements.txt"

    if not requirements_file.exists():
        print(f"❌ requirements.txt not found at {requirements_file}")
        sys.exit(1)

    print(f"📄 Found requirements.txt at {requirements_file}")

    # Install dependencies
    if not install_dependencies(requirements_file):
        print("\n❌ Failed to install dependencies. Please check requirements.txt")
        sys.exit(1)

    print()

    # Check for conflicts
    check_conflicts(requirements_file)

    print()

    # Verify imports
    if verify_imports():
        print("\n✅ All dependencies installed and verified successfully!")
        print("🚀 Ready to deploy!")
        sys.exit(0)
    else:
        print("\n⚠️  Some imports failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
