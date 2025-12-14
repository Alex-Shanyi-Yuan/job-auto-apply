'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { applyForJob } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';

export default function ApplyPage() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await applyForJob(url);
      router.push('/dashboard');
    } catch (err) {
      setError('Failed to start application process. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto pt-8">
      <Card>
        <CardHeader>
          <CardTitle>New Application</CardTitle>
          <CardDescription>
            Enter the URL of the job posting you want to apply for.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="url">Job Posting URL</Label>
              <Input
                id="url"
                type="url"
                required
                placeholder="https://linkedin.com/jobs/..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={loading}
              />
              <p className="text-sm text-muted-foreground">
                We'll scrape the job description and tailor your resume automatically.
              </p>
            </div>

            {error && (
              <div className="text-destructive text-sm">{error}</div>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Starting Process...
                </>
              ) : (
                'Generate Application'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
