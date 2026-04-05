'use client';

import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { getJobs, Job } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { StageProgress } from '@/components/ui/stage-progress';
import { JobStageEditor } from '@/components/ui/job-stage-editor';
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
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const isFetchingRef = useRef(false);

  useEffect(() => {
    async function fetchJobs() {
      if (isFetchingRef.current) {
        return;
      }
      isFetchingRef.current = true;
      try {
        const data = await getJobs();
        setJobs(data);
      } catch (err) {
        console.error(err);
      } finally {
        isFetchingRef.current = false;
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
      case 'active':
        return <Badge variant="default">Active</Badge>;
      case 'processing':
        return <Badge variant="secondary">Processing</Badge>;
      case 'rejected':
        return <Badge variant="destructive">Rejected</Badge>;
      case 'dismissed':
        return <Badge variant="outline">Dismissed</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const toggleRowExpansion = (jobId: number) => {
    setExpandedRows((previous) => {
      const next = new Set(previous);
      if (next.has(jobId)) {
        next.delete(jobId);
      } else {
        next.add(jobId);
      }
      return next;
    });
  };

  const handleJobUpdate = (updatedJob: Job) => {
    setJobs((previous) =>
      previous.map((job) => (job.id === updatedJob.id ? updatedJob : job))
    );
  };

  const renderJobRows = (job: Job) => {
    const isExpanded = expandedRows.has(job.id);
    const detailsRowId = `job-stage-editor-${job.id}`;

    return (
      <Fragment key={job.id}>
        <TableRow>
          <TableCell>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              title={isExpanded ? 'Collapse row' : 'Expand row'}
              aria-expanded={isExpanded}
              aria-controls={detailsRowId}
              onClick={() => toggleRowExpansion(job.id)}
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </Button>
          </TableCell>
          <TableCell>
            {new Date(job.created_at).toLocaleDateString()}
          </TableCell>
          <TableCell className="font-medium">{job.company}</TableCell>
          <TableCell>{job.title}</TableCell>
          <TableCell>{getStatusBadge(job.status)}</TableCell>
          <TableCell>
            <StageProgress stages={job.stages} />
          </TableCell>
          <TableCell className="text-right">
            <div className="flex justify-end gap-2">
              <Button asChild variant="ghost" size="icon" title="View Details">
                <Link href={`/jobs/${job.id}`}>
                  <FileText className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="ghost" size="icon" title="View Original Posting">
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              </Button>
            </div>
          </TableCell>
        </TableRow>
        {isExpanded && (
          <TableRow id={detailsRowId}>
            <TableCell colSpan={7} className="bg-muted/20">
              <JobStageEditor job={job} onUpdate={handleJobUpdate} />
            </TableCell>
          </TableRow>
        )}
      </Fragment>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <Button asChild>
          <Link href="/apply">
            <PlusCircle className="mr-2 h-4 w-4" />
            New Application
          </Link>
        </Button>
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
                  <TableHead className="w-12" />
                  <TableHead>Date</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Stages</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {todayJobs.map(renderJobRows)}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Older Applications */}
      {olderJobs.length > 0 && (
        <Card>
          <CardHeader className="rounded-t-lg py-3">
            <button
              type="button"
              className="flex w-full items-center justify-between rounded-md px-1 text-left hover:bg-gray-50"
              aria-expanded={showOlderJobs}
              onClick={() => setShowOlderJobs(!showOlderJobs)}
            >
              <CardTitle className="flex items-center justify-between w-full">
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
            </button>
          </CardHeader>
          {showOlderJobs && (
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12" />
                    <TableHead>Date</TableHead>
                    <TableHead>Company</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Stages</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {olderJobs.map(renderJobRows)}
                </TableBody>
              </Table>
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}
