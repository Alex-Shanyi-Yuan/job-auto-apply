"""
Module 1: LaTeX Parser
Reads .tex files and extracts mutable sections
"""
import re
from typing import Dict

def extract_mutable_sections(tex_content: str) -> Dict[str, str]:
    """
    Extract content between % <TAG> and % </TAG> markers
    
    Args:
        tex_content: The full LaTeX document as a string
        
    Returns:
        Dictionary mapping tag names to their content
    """
    sections = {}
    
    # Pattern to match % <TAG_NAME> content % </TAG_NAME>
    pattern = r'%\s*<(\w+)>(.*?)%\s*</\1>'
    
    matches = re.finditer(pattern, tex_content, re.DOTALL)
    
    for match in matches:
        tag_name = match.group(1).lower()
        content = match.group(2).strip()
        sections[tag_name] = content
    
    return sections

def load_template(file_path: str) -> tuple[str, Dict[str, str]]:
    """
    Load LaTeX template and extract mutable sections
    
    Returns:
        Tuple of (full_template, mutable_sections)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        full_template = f.read()
    
    mutable_sections = extract_mutable_sections(full_template)
    
    return full_template, mutable_sections
