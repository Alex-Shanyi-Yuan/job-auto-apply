'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { getJobs, Job } from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PlusCircle, ExternalLink, FileText, ChevronDown, ChevronRight } from 'lucide-react';

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [showOlderJobs, setShowOlderJobs] = useState(false);

  useEffect(() => {
    async function fetchJobs() {
      try {
        const data = await getJobs();
        setJobs(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    
    fetchJobs();
    
    // Poll every 5 seconds
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  // Helper to check if a date is today
  const isToday = (dateString: string) => {
    const date = new Date(dateString);
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  // Group jobs by today vs older
  const { todayJobs, olderJobs } = useMemo(() => {
    const today: Job[] = [];
    const older: Job[] = [];
    
    jobs.forEach(job => {
      if (isToday(job.created_at)) {
        today.push(job);
      } else {
        older.push(job);
      }
    });
    
    return { todayJobs: today, olderJobs: older };
  }, [jobs]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'applied':
        return <Badge variant="default">Applied</Badge>;
      case 'processing':
        return <Badge variant="secondary">Processing</Badge>;
      case 'interviewing':
        return <Badge className="bg-green-500 hover:bg-green-600">Interviewing</Badge>;
      case 'rejected':
        return <Badge variant="destructive">Rejected</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const renderJobRow = (job: Job) => (
    <TableRow key={job.id}>
      <TableCell>
        {new Date(job.created_at).toLocaleDateString()}
      </TableCell>
      <TableCell className="font-medium">{job.company}</TableCell>
      <TableCell>{job.title}</TableCell>
      <TableCell>{getStatusBadge(job.status)}</TableCell>
      <TableCell className="text-right">
        <div className="flex justify-end gap-2">
          <Link href={`/jobs/${job.id}`}>
            <Button variant="ghost" size="icon" title="View Details">
              <FileText className="h-4 w-4" />
            </Button>
          </Link>
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            title="View Original Posting"
          >
            <Button variant="ghost" size="icon">
              <ExternalLink className="h-4 w-4" />
            </Button>
          </a>
        </div>
      </TableCell>
    </TableRow>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <Link href="/apply">
          <Button>
            <PlusCircle className="mr-2 h-4 w-4" />
            New Application
          </Button>
        </Link>
      </div>

      {/* Today's Applications */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span>Today&apos;s Applications</span>
            <Badge variant="secondary">{todayJobs.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-4">Loading jobs...</div>
          ) : todayJobs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No applications today. Start by applying to a job!
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {todayJobs.map(renderJobRow)}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Older Applications */}
      {olderJobs.length > 0 && (
        <Card>
          <CardHeader 
            className="cursor-pointer hover:bg-gray-50 transition-colors rounded-t-lg"
            onClick={() => setShowOlderJobs(!showOlderJobs)}
          >
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {showOlderJobs ? (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronRight className="h-5 w-5 text-gray-500" />
                )}
                <span>Previous Applications</span>
                <Badge variant="outline">{olderJobs.length}</Badge>
              </div>
              <span className="text-sm font-normal text-gray-500">
                {showOlderJobs ? 'Click to collapse' : 'Click to expand'}
              </span>
            </CardTitle>
          </CardHeader>
          {showOlderJobs && (
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Company</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {olderJobs.map(renderJobRow)}
                </TableBody>
              </Table>
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}
