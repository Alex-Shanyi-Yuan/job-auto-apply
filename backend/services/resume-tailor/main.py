#!/usr/bin/env python3
"""
Resume Tailor CLI - Main Entry Point
Coordinates job scraping, LLM tailoring, and PDF compilation.
"""

import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core import fetch_job_description, tailor_resume, compile_pdf


def load_master_resume(file_path: str = "./data/master.tex") -> str:
    """
    Load the master resume LaTeX file.
    
    Args:
        file_path: Path to master.tex
        
    Returns:
        LaTeX content as string
        
    Raises:
        FileNotFoundError: If master.tex doesn't exist
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(
            f"Master resume not found: {file_path}\n"
            f"Please create a LaTeX resume at {file_path}"
        )
    
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_company_name(job_description: str) -> str:
    """
    Attempt to extract company name from job description.
    Uses simple heuristics - looks for common patterns.
    
    Args:
        job_description: Job description text
        
    Returns:
        Company name or "Company" as fallback
    """
    import re
    
    # Look for patterns like "at [Company]" or "[Company] is"
    patterns = [
        r'at\s+([A-Z][A-Za-z\s&]+?)(?:\s+is|\s+in|\s+has|\.|,)',
        r'([A-Z][A-Za-z\s&]+?)\s+is\s+(?:looking|seeking|hiring)',
        r'Join\s+([A-Z][A-Za-z\s&]+?)(?:\s+and|\s+as|\.)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, job_description)
        if match:
            company = match.group(1).strip()
            # Validate it's not too long and doesn't contain weird chars
            if len(company) < 50 and company.replace(' ', '').replace('&', '').isalnum():
                return company
    
    return "Company"


def main():
    """Main CLI function."""
    
    # Load environment variables
    load_dotenv()
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Resume Tailor - Automatically tailor your LaTeX resume to job descriptions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --url "https://jobs.example.com/posting"
  python main.py --file "job_description.txt"
  python main.py --text "Senior Engineer position at TechCorp..."
  python main.py --url "https://..." --output "GoogleSWE"
        """
    )
    
    # Input source arguments (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--url',
        type=str,
        help='URL of the job posting to fetch'
    )
    input_group.add_argument(
        '--file',
        type=str,
        help='Path to text file containing job description'
    )
    input_group.add_argument(
        '--text',
        type=str,
        help='Job description as direct text input'
    )
    
    # Optional arguments
    parser.add_argument(
        '--master',
        type=str,
        default='./data/master.tex',
        help='Path to master resume LaTeX file (default: ./data/master.tex)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Custom output filename prefix (default: auto-detected company name)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./output',
        help='Output directory for generated files (default: ./output)'
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Keep auxiliary LaTeX files (.aux, .log, etc.)'
    )
    
    args = parser.parse_args()
    
    try:
        print("=" * 60)
        print("Resume Tailor CLI".center(60))
        print("=" * 60)
        print()
        
        # Step 1: Load master resume
        print("📄 Loading master resume...")
        master_latex = load_master_resume(args.master)
        print(f"   ✓ Loaded {len(master_latex)} characters from {args.master}")
        print()
        
        # Step 2: Fetch job description
        print("🔍 Fetching job description...")
        
        if args.url:
            print(f"   Source: {args.url}")
            job_description = fetch_job_description(url=args.url)
        elif args.file:
            print(f"   Source: {args.file}")
            job_description = fetch_job_description(file_path=args.file)
        else:
            print(f"   Source: Direct text input")
            job_description = fetch_job_description(text=args.text)
        
        print(f"   ✓ Retrieved {len(job_description)} characters")
        print()
        
        # Step 3: Tailor resume with Gemini
        print("🤖 Tailoring resume with Gemini Pro...")
        print("   (This may take 10-30 seconds...)")
        
        tailored_latex = tailor_resume(master_latex, job_description)
        
        print(f"   ✓ Received tailored resume ({len(tailored_latex)} characters)")
        print()
        
        # Step 4: Compile to PDF
        print("📄 Compiling LaTeX to PDF...")
        
        # Determine output filename
        company_name = args.output or extract_company_name(job_description)
        
        pdf_path = compile_pdf(
            latex_content=tailored_latex,
            output_dir=args.output_dir,
            company_name=company_name,
            cleanup=not args.no_cleanup
        )
        
        print()
        print("=" * 60)
        print("🎉 Success!".center(60))
        print("=" * 60)
        print()
        print(f"Resume saved to: {pdf_path}")
        print()
        
        return 0
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return 1
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print()
        print("Make sure to set GOOGLE_API_KEY in your .env file")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print()
        print("Full error details:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

