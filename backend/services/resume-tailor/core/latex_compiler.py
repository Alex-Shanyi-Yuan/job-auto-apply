"""
Module 3: LaTeX Compiler
Compiles LaTeX files to PDF using pdflatex.
"""

import subprocess
import os
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple


class LaTeXCompiler:
    """Handles LaTeX compilation to PDF."""
    
    def __init__(self, output_dir: str = "./output"):
        """
        Initialize the compiler.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def check_pdflatex_installed(self) -> bool:
        """
        Check if pdflatex is available in the system.
        
        Returns:
            True if pdflatex is found, False otherwise
        """
        try:
            result = subprocess.run(
                ['pdflatex', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def write_tex_file(self, latex_content: str, filename: str = "tailored_resume.tex") -> Path:
        """
        Write LaTeX content to a file.
        
        Args:
            latex_content: LaTeX document content
            filename: Output filename
            
        Returns:
            Path to the written file
        """
        tex_path = self.output_dir / filename
        
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        return tex_path
    
    def compile_latex(self, tex_path: Path, passes: int = 2) -> Tuple[bool, str]:
        """
        Compile LaTeX file to PDF.
        
        Args:
            tex_path: Path to .tex file
            passes: Number of compilation passes (default 2 for references)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.check_pdflatex_installed():
            return False, (
                "pdflatex not found in system PATH.\n"
                "Please install TeX Live, MacTeX, or MiKTeX.\n"
                "Or use Docker: docker-compose run tailor --url <url>"
            )
        
        try:
            # Run pdflatex multiple times for references
            for i in range(passes):
                result = subprocess.run(
                    [
                        'pdflatex',
                        '-interaction=nonstopmode',
                        f'-output-directory={self.output_dir}',
                        str(tex_path)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    # Save log for debugging
                    log_path = tex_path.with_suffix('.log')
                    error_msg = f"LaTeX compilation failed.\nCheck log file: {log_path}\n"
                    
                    if result.stderr:
                        error_msg += f"\nError output:\n{result.stderr[:500]}"
                    
                    return False, error_msg
            
            return True, "Compilation successful"
            
        except subprocess.TimeoutExpired:
            return False, "Compilation timed out after 30 seconds"
        except Exception as e:
            return False, f"Compilation error: {str(e)}"
    
    def cleanup_auxiliary_files(self, base_name: str):
        """
        Remove auxiliary LaTeX files (.aux, .log, .out, etc.).
        
        Args:
            base_name: Base filename without extension
        """
        extensions = ['.aux', '.log', '.out', '.toc', '.lof', '.lot']
        
        for ext in extensions:
            file_path = self.output_dir / f"{base_name}{ext}"
            if file_path.exists():
                file_path.unlink()
    
    def rename_output_pdf(
        self,
        temp_name: str,
        company_name: str = "Company",
        include_date: bool = True
    ) -> Path:
        """
        Rename the generated PDF with a descriptive name.
        
        Args:
            temp_name: Current PDF filename (without .pdf)
            company_name: Company name for the filename
            include_date: Whether to include date in filename
            
        Returns:
            Path to the renamed PDF
        """
        old_path = self.output_dir / f"{temp_name}.pdf"
        
        if not old_path.exists():
            raise FileNotFoundError(f"PDF not found: {old_path}")
        
        # Create new filename
        date_str = datetime.now().strftime("%Y-%m-%d") if include_date else ""
        parts = ["Resume", company_name.replace(" ", "_")]
        if date_str:
            parts.append(date_str)
        
        new_name = "_".join(parts) + ".pdf"
        new_path = self.output_dir / new_name
        
        # Handle existing file
        if new_path.exists():
            counter = 1
            while new_path.exists():
                new_name = "_".join(parts) + f"_{counter}.pdf"
                new_path = self.output_dir / new_name
                counter += 1
        
        # Rename
        shutil.move(str(old_path), str(new_path))
        
        return new_path


def compile_pdf(
    latex_content: str,
    output_dir: str = "./output",
    company_name: str = "Company",
    cleanup: bool = True
) -> str:
    """
    Compile LaTeX content to PDF.
    
    Args:
        latex_content: Complete LaTeX document as string
        output_dir: Directory for output files
        company_name: Company name for PDF filename
        cleanup: Whether to remove auxiliary files
        
    Returns:
        Path to the generated PDF file
        
    Raises:
        Exception: If compilation fails
    """
    compiler = LaTeXCompiler(output_dir=output_dir)
    
    # Generate unique filename for intermediate files
    unique_id = str(uuid.uuid4())
    tex_filename = f"resume_{unique_id}.tex"
    
    # Write LaTeX file
    tex_path = compiler.write_tex_file(latex_content, filename=tex_filename)
    print(f"✓ LaTeX file written to: {tex_path}")
    
    # Compile to PDF
    print("Compiling to PDF...")
    success, message = compiler.compile_latex(tex_path)
    
    if not success:
        raise Exception(f"PDF compilation failed: {message}")
    
    print("✓ PDF compiled successfully")
    
    # Rename PDF
    base_name = tex_path.stem
    pdf_path = compiler.rename_output_pdf(base_name, company_name)
    print(f"✓ PDF saved as: {pdf_path}")
    
    # Cleanup auxiliary files
    if cleanup:
        compiler.cleanup_auxiliary_files(base_name)
        # Also remove the intermediate .tex file
        if tex_path.exists():
            tex_path.unlink()
        print("✓ Auxiliary files cleaned up")
    
    return str(pdf_path.absolute())


if __name__ == "__main__":
    # Test compilation with a simple LaTeX document
    test_latex = r"""
\documentclass{article}
\usepackage[utf8]{inputenc}

\title{Test Resume}
\author{John Doe}
\date{}

\begin{document}

\maketitle

\section{Summary}
Experienced software engineer with expertise in Python and cloud technologies.

\section{Experience}
\textbf{Senior Engineer} - Tech Corp (2020-2024)
\begin{itemize}
    \item Led development of microservices architecture
    \item Improved system performance by 50\%
\end{itemize}

\end{document}
"""
    
    try:
        pdf_path = compile_pdf(test_latex, company_name="TestCompany")
        print(f"\n✓ Test successful! PDF created at: {pdf_path}")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
