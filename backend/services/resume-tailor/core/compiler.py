"""
Module 3: LaTeX Compiler
Compiles .tex files to PDF using pdflatex
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict

def inject_tailored_content(template: str, tailored_sections: Dict[str, str]) -> str:
    """
    Replace content between % <TAG> markers with tailored content
    
    Args:
        template: The full LaTeX template
        tailored_sections: Dictionary mapping tag names to new content
        
    Returns:
        Modified LaTeX document
    """
    result = template
    
    for tag_name, new_content in tailored_sections.items():
        tag_upper = tag_name.upper()
        pattern = f'(%\\s*<{tag_upper}>).*?(%\\s*</{tag_upper}>)'
        replacement = f'\\1\n{new_content}\n\\2'
        
        import re
        result = re.sub(pattern, replacement, result, flags=re.DOTALL)
    
    return result

def compile_latex_to_pdf(tex_content: str, output_dir: str = None) -> str:
    """
    Compile LaTeX content to PDF
    
    Args:
        tex_content: The LaTeX document as a string
        output_dir: Directory to save output (default: temp directory)
        
    Returns:
        Path to the generated PDF file
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    
    # Write .tex file
    tex_path = os.path.join(output_dir, 'resume.tex')
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(tex_content)
    
    # Run pdflatex
    try:
        subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', '-output-directory', output_dir, tex_path],
            check=True,
            capture_output=True,
            timeout=30
        )
    except subprocess.CalledProcessError as e:
        raise Exception(f"LaTeX compilation failed: {e.stderr.decode()}")
    
    pdf_path = os.path.join(output_dir, 'resume.pdf')
    
    if not os.path.exists(pdf_path):
        raise Exception("PDF was not generated")
    
    return pdf_path
