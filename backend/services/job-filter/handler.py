import json
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def handler(event, context):
    """
    AWS Lambda handler for job filtering
    Determines if a candidate is a good match for a job
    """
    body = json.loads(event.get('body', '{}'))
    user_profile = body.get('userProfile', {})
    job_description = body.get('jobDescription', '')
    
    # Use LLM to evaluate match
    prompt = f"""
    Evaluate if this candidate is a good match for this job.
    
    Candidate Profile:
    {json.dumps(user_profile, indent=2)}
    
    Job Description:
    {job_description}
    
    Provide a match score (0-100) and brief reason.
    Respond in JSON format: {{"match_score": number, "reason": "string"}}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
