"""
Module 2: LLM Client
Handles interactions with OpenAI/Anthropic for content tailoring
"""
import os
from typing import Dict
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def tailor_summary(original_summary: str, job_description: str) -> str:
    """
    Rewrite resume summary to match job description
    """
    prompt = f"""
    Rewrite this resume summary to align with the job description.
    Use keywords from the job description.
    Return only the rewritten text, no explanations.
    
    Original Summary:
    {original_summary}
    
    Job Description:
    {job_description}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()

def tailor_bullets(original_bullets: str, job_description: str) -> str:
    """
    Select and rewrite the most relevant bullet points
    """
    prompt = f"""
    Here are the candidate's original bullet points in LaTeX format:
    {original_bullets}
    
    Job Description:
    {job_description}
    
    Select the top 4 most relevant bullet points and rewrite them to emphasize impact.
    Return them as valid LaTeX \\item statements.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()

def filter_skills(skills: str, job_description: str) -> str:
    """
    Filter skills to only those relevant to the job
    """
    prompt = f"""
    Filter this list of skills. Keep only those mentioned in or highly relevant to the job description.
    Return as a comma-separated string.
    
    Skills: {skills}
    
    Job Description:
    {job_description}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    return response.choices[0].message.content.strip()
