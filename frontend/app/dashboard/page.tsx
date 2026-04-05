'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { getJobs, Job, JobWithStagesResponse, StageName, updateJobStages } from '@/lib/api';
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

const STAGE_ORDER = ['applied', 'oa', 'interview', 'offer'] as const satisfies readonly StageName[];
const STAGE_LABELS: Record<StageName, string> = {
  applied: 'Applied',
  oa: 'OA',
  interview: 'Interview',
  offer: 'Offer',
};

function mergeJobUpdate(previous: Job, response: JobWithStagesResponse): Job {
  return {
    ...previous,
    id: response.id,
    url: response.url,
    company: response.company,
    title: response.title,
    status: response.status,
    score: response.score,
    stages: response.stages,
    rejection_stage: response.rejection_stage ?? null,
    rejection_reason: response.rejection_reason ?? null,
    created_at: response.created_at,
    updated_at: response.updated_at,
  };
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [showOlderJobs, setShowOlderJobs] = useState(false);
  const [updatingJobIds, setUpdatingJobIds] = useState<Set<number>>(new Set());
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
      case 'offer':
        return <Badge className="bg-green-600 hover:bg-green-700">Offer</Badge>;
      case 'processing':
        return <Badge variant="secondary">Processing</Badge>;
      case 'rejected':
        return <Badge variant="destructive">Rejected</Badge>;
      case 'turndown':
        return <Badge variant="outline">TurnDown</Badge>;
      case 'dismissed':
        return <Badge variant="outline">Dismissed</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const latestCompletedStage = (completed: Set<StageName>): StageName => {
    for (let i = STAGE_ORDER.length - 1; i >= 0; i -= 1) {
      const stage = STAGE_ORDER[i];
      if (completed.has(stage)) {
        return stage;
      }
    }
    return 'applied';
  };

  const stageSetForJob = (job: Job) =>
    new Set((job.stages ?? []).filter((stage) => stage.completed_at).map((stage) => stage.stage_name));

  const noteMapForJob = (job: Job) =>
    new Map((job.stages ?? []).map((stage) => [stage.stage_name, stage.notes ?? null] as const));

  const handleToggleStage = async (job: Job, stageName: StageName) => {
    if (updatingJobIds.has(job.id)) {
      return;
    }

    const completed = stageSetForJob(job);
    const notes = noteMapForJob(job);
    const currentlyCompleted = completed.has(stageName);
    const nextCompleted = !currentlyCompleted;

    setUpdatingJobIds((previous) => new Set(previous).add(job.id));
    try {
      const response = await updateJobStages(job.id, {
        stages: STAGE_ORDER.map((stage) => ({
          name: stage,
          completed: stage === stageName ? nextCompleted : completed.has(stage),
          notes: notes.get(stage) ?? null,
        })),
      });
      setJobs((previous) =>
        previous.map((candidate) =>
          candidate.id === job.id ? mergeJobUpdate(candidate, response) : candidate
        )
      );
    } catch (error) {
      console.error('Failed to toggle stage', error);
    } finally {
      setUpdatingJobIds((previous) => {
        const next = new Set(previous);
        next.delete(job.id);
        return next;
      });
    }
  };

  const handleToggleStatus = async (job: Job) => {
    if (updatingJobIds.has(job.id)) {
      return;
    }
    if (job.status !== 'active' && job.status !== 'rejected' && job.status !== 'turndown') {
      return;
    }

    const completed = stageSetForJob(job);
    const notes = noteMapForJob(job);
    const nextStatus =
      job.status === 'active'
        ? 'rejected'
        : job.status === 'rejected'
          ? 'turndown'
          : 'active';

    setUpdatingJobIds((previous) => new Set(previous).add(job.id));
    try {
      const response = await updateJobStages(job.id, {
        stages: STAGE_ORDER.map((stage) => ({
          name: stage,
          completed: completed.has(stage),
          notes: notes.get(stage) ?? null,
        })),
        rejection_stage: nextStatus === 'rejected' ? latestCompletedStage(completed) : null,
        rejection_reason: nextStatus === 'rejected' ? (job.rejection_reason ?? null) : null,
        status_override: nextStatus,
      });
      setJobs((previous) =>
        previous.map((candidate) =>
          candidate.id === job.id ? mergeJobUpdate(candidate, response) : candidate
        )
      );
    } catch (error) {
      console.error('Failed to toggle status', error);
    } finally {
      setUpdatingJobIds((previous) => {
        const next = new Set(previous);
        next.delete(job.id);
        return next;
      });
    }
  };

  const renderStageButtons = (job: Job) => {
    const completed = stageSetForJob(job);
    const isUpdating = updatingJobIds.has(job.id);

    return (
      <div className="flex flex-wrap items-center gap-1">
        {STAGE_ORDER.map((stage) => {
          const isCompleted = completed.has(stage);
          return (
            <Button
              key={stage}
              type="button"
              size="sm"
              variant={isCompleted ? 'default' : 'outline'}
              className="h-7 px-2 text-xs"
              disabled={isUpdating}
              onClick={() => handleToggleStage(job, stage)}
              title={`${STAGE_LABELS[stage]}: ${isCompleted ? 'on' : 'off'}`}
            >
              {STAGE_LABELS[stage]}
            </Button>
          );
        })}
      </div>
    );
  };

  const renderJobRow = (job: Job) => {
    const isUpdating = updatingJobIds.has(job.id);
    const isToggleableStatus = job.status === 'active' || job.status === 'rejected' || job.status === 'turndown';
    return (
      <TableRow key={job.id}>
        <TableCell>
          {new Date(job.created_at).toLocaleDateString()}
        </TableCell>
        <TableCell className="font-medium">{job.company}</TableCell>
        <TableCell>{job.title}</TableCell>
        <TableCell>
          {isToggleableStatus ? (
            <Button
              type="button"
              variant="ghost"
              className="h-auto p-0"
              disabled={isUpdating}
              onClick={() => handleToggleStatus(job)}
              title="Toggle Active/Rejected/TurnDown"
            >
              {getStatusBadge(job.status)}
            </Button>
          ) : (
            getStatusBadge(job.status)
          )}
        </TableCell>
        <TableCell>{renderStageButtons(job)}</TableCell>
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
                  <TableHead>Date</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Stages</TableHead>
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
                    <TableHead>Date</TableHead>
                    <TableHead>Company</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Stages</TableHead>
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
