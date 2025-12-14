'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getJob, getResumePdfUrl, Job } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { ExternalLink, Calendar, Building2, Loader2, FileText } from 'lucide-react';

export default function JobDetailsPage() {
  const params = useParams();
  const id = Number(params.id);
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchJob() {
      try {
        const data = await getJob(id);
        setJob(data);
      } catch (err) {
        setError('Failed to load job details');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    if (id) {
      fetchJob();
    }
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="flex items-center justify-center h-[50vh] text-destructive">
        {error || 'Job not found'}
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{job.title}</h1>
          <div className="flex items-center gap-4 mt-2 text-muted-foreground">
            <div className="flex items-center gap-1">
              <Building2 className="h-4 w-4" />
              <span>{job.company}</span>
            </div>
            <div className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              <span>{new Date(job.created_at).toLocaleDateString()}</span>
            </div>
            <Badge variant={job.status === 'applied' ? 'default' : 'secondary'}>
              {job.status}
            </Badge>
          </div>
        </div>
        <a 
          href={job.url} 
          target="_blank" 
          rel="noopener noreferrer"
        >
          <Button variant="outline">
            <ExternalLink className="mr-2 h-4 w-4" />
            Original Posting
          </Button>
        </a>
      </div>

      <Card className="flex-1 overflow-hidden flex flex-col">
        <CardContent className="p-6 flex-1 overflow-auto">
          {job.status === 'processing' ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-4">
                <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
                <p className="text-muted-foreground">
                  Tailoring resume... This may take a minute.
                </p>
              </div>
            </div>
          ) : job.status === 'failed' ? (
            <div className="flex items-center justify-center h-full text-destructive">
              Failed to generate resume. Please check the logs.
            </div>
          ) : (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Tailored Resume</h2>
                <a href={getResumePdfUrl(job.id)} download>
                  <Button>
                    <FileText className="mr-2 h-4 w-4" />
                    Download PDF
                  </Button>
                </a>
              </div>
              
              {job.requirements && job.requirements.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium mb-3">Key Requirements Identified</h3>
                  <div className="flex flex-wrap gap-2">
                    {job.requirements.map((req, i) => (
                      <Badge key={i} variant="secondary" className="text-sm py-1 px-3">
                        {req}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="bg-muted/30 p-4 rounded-lg border">
                <p className="text-sm text-muted-foreground text-center">
                  Resume has been tailored for this position. Click the download button above to view the PDF.
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
