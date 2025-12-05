"""
Utility script to seed DynamoDB with sample job data
"""
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))

def seed_jobs():
    """Add sample jobs to DynamoDB"""
    table_name = os.getenv('DYNAMODB_JOBS_TABLE', 'autocareer-jobs')
    table = dynamodb.Table(table_name)
    
    sample_jobs = [
        {
            'jobId': 'job-001',
            'title': 'Senior Software Engineer',
            'company': 'Tech Corp',
            'salary': 150000,
            'location': 'San Francisco, CA',
            'description': 'Build scalable backend systems...',
            'createdAt': datetime.utcnow().isoformat()
        },
        {
            'jobId': 'job-002',
            'title': 'Full Stack Developer',
            'company': 'Startup Inc',
            'salary': 130000,
            'location': 'Remote',
            'description': 'Work on exciting new features...',
            'createdAt': datetime.utcnow().isoformat()
        }
    ]
    
    for job in sample_jobs:
        table.put_item(Item=job)
        print(f"Added job: {job['title']} at {job['company']}")

if __name__ == '__main__':
    seed_jobs()
    print("Seeding completed!")
