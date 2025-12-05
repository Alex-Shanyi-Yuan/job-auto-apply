#!/usr/bin/env python3
"""
Setup Verification Script
Checks if your environment is properly configured to run Resume Tailor.
"""

import sys
import os
from pathlib import Path


def check_python_version():
    """Check Python version."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"   ✓ Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"   ✗ Python {version.major}.{version.minor}.{version.micro} (Need 3.11+)")
        return False


def check_dependencies():
    """Check if required packages are installed."""
    print("\n📦 Checking Python dependencies...")
    
    required = {
        'requests': 'requests',
        'beautifulsoup4': 'bs4',
        'google-generativeai': 'google.generativeai',
        'python-dotenv': 'dotenv'
    }
    
    all_ok = True
    for package, import_name in required.items():
        try:
            __import__(import_name)
            print(f"   ✓ {package}")
        except ImportError:
            print(f"   ✗ {package} (run: pip install {package})")
            all_ok = False
    
    return all_ok


def check_env_file():
    """Check if .env file exists and has API key."""
    print("\n🔑 Checking environment configuration...")
    
    env_path = Path('.env')
    if not env_path.exists():
        print("   ✗ .env file not found")
        print("   → Run: copy .env.example .env")
        print("   → Then edit .env with your GOOGLE_API_KEY")
        return False
    
    print("   ✓ .env file exists")
    
    # Check if API key is set
    with open(env_path, 'r') as f:
        content = f.read()
    
    if 'GOOGLE_API_KEY=' in content and 'your_gemini_api_key_here' not in content:
        # Check if it's not empty
        for line in content.split('\n'):
            if line.startswith('GOOGLE_API_KEY='):
                key = line.split('=', 1)[1].strip()
                if key and len(key) > 20:
                    print(f"   ✓ GOOGLE_API_KEY is set ({len(key)} characters)")
                    return True
                else:
                    print("   ✗ GOOGLE_API_KEY appears to be empty or invalid")
                    return False
    
    print("   ✗ GOOGLE_API_KEY not properly configured")
    print("   → Get your key from: https://makersuite.google.com/app/apikey")
    return False


def check_master_resume():
    """Check if master resume exists."""
    print("\n📄 Checking master resume...")
    
    master_path = Path('data/master.tex')
    if not master_path.exists():
        print("   ✗ data/master.tex not found")
        print("   → Create your LaTeX resume at data/master.tex")
        return False
    
    size = master_path.stat().st_size
    print(f"   ✓ data/master.tex exists ({size} bytes)")
    
    if size < 100:
        print("   ⚠ Warning: File seems very small. Is it complete?")
        return True
    
    return True


def check_pdflatex():
    """Check if pdflatex is installed."""
    print("\n📝 Checking LaTeX installation...")
    
    import subprocess
    try:
        result = subprocess.run(
            ['pdflatex', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Extract version from output
            first_line = result.stdout.split('\n')[0]
            print(f"   ✓ pdflatex found: {first_line}")
            return True
        else:
            print("   ✗ pdflatex command failed")
            return False
    except FileNotFoundError:
        print("   ✗ pdflatex not found in PATH")
        print("   → Install TeX Live, MacTeX, or MiKTeX")
        print("   → OR use Docker: docker-compose run tailor")
        return False
    except Exception as e:
        print(f"   ✗ Error checking pdflatex: {e}")
        return False


def check_directories():
    """Check if required directories exist."""
    print("\n📁 Checking directory structure...")
    
    dirs = ['core', 'data', 'output']
    all_ok = True
    
    for dir_name in dirs:
        path = Path(dir_name)
        if path.exists() and path.is_dir():
            print(f"   ✓ {dir_name}/")
        else:
            print(f"   ✗ {dir_name}/ (creating...)")
            path.mkdir(exist_ok=True)
            all_ok = False
    
    return all_ok


def main():
    """Run all checks."""
    print("=" * 60)
    print("Resume Tailor - Setup Verification".center(60))
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment Config", check_env_file),
        ("Master Resume", check_master_resume),
        ("Directory Structure", check_directories),
        ("LaTeX Installation", check_pdflatex),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"   ✗ Error during check: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary".center(60))
    print("=" * 60)
    print()
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    print()
    print(f"Passed: {passed}/{total}")
    print()
    
    if passed == total:
        print("🎉 All checks passed! You're ready to use Resume Tailor.")
        print()
        print("Try running:")
        print("  python main.py --text 'Software Engineer at TechCorp'")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print()
        print("Common solutions:")
        print("  - Missing dependencies: pip install -r requirements.txt")
        print("  - No API key: copy .env.example .env, then edit .env")
        print("  - No pdflatex: Use Docker instead (docker-compose run tailor)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
