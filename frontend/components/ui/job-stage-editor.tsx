'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Job, JobWithStagesResponse, StageName, StageUpdate, updateJobStages } from '@/lib/api'

const STAGE_ORDER = ['applied', 'oa', 'interview', 'offer'] as const satisfies readonly StageName[]

const STAGE_LABELS: Record<StageName, string> = {
  applied: 'Applied',
  oa: 'OA',
  interview: 'Interview',
  offer: 'Offer',
}

interface JobStageEditorProps {
  job: Job
  onUpdate: (updatedJob: Job) => void
}

function toUpdatedJob(previous: Job, response: JobWithStagesResponse): Job {
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
  }
}

function getStageNotes(stages?: Job['stages']): Record<StageName, string> {
  const byName = new Map((stages ?? []).map((stage) => [stage.stage_name, stage.notes ?? '']))
  return {
    applied: byName.get('applied') ?? '',
    oa: byName.get('oa') ?? '',
    interview: byName.get('interview') ?? '',
    offer: byName.get('offer') ?? '',
  }
}

function parseStageName(value: string): StageName | '' {
  return STAGE_ORDER.some((stage) => stage === value) ? (value as StageName) : ''
}

export function JobStageEditor({ job, onUpdate }: JobStageEditorProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [activeSaveCount, setActiveSaveCount] = useState(0)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [showRejectionForm, setShowRejectionForm] = useState(false)
  const [rejectionStage, setRejectionStage] = useState<StageName | ''>(job.rejection_stage ?? '')
  const [rejectionReason, setRejectionReason] = useState(job.rejection_reason ?? '')
  const [noteDrafts, setNoteDrafts] = useState<Record<StageName, string>>(() => getStageNotes(job.stages))
  const [pendingNoteStage, setPendingNoteStage] = useState<StageName | null>(null)
  const requestVersionRef = useRef(0)
  const latestJobRef = useRef(job)
  const isSaving = activeSaveCount > 0

  const completedStages = useMemo(
    () => new Set((job.stages ?? []).filter((stage) => stage.completed_at).map((stage) => stage.stage_name)),
    [job.stages]
  )

  useEffect(() => {
    latestJobRef.current = job
  }, [job])

  useEffect(() => {
    setRejectionStage(job.rejection_stage ?? '')
    setRejectionReason(job.rejection_reason ?? '')
    setNoteDrafts(getStageNotes(job.stages))
  }, [job.id, job.updated_at, job.rejection_reason, job.rejection_stage, job.stages])

  const saveUpdate = async (
    stageFactory: (completed: Set<StageName>, notes: Record<StageName, string>) => StageUpdate[],
    rejection?: { stage: StageName | ''; reason: string },
    notesOverride?: Record<StageName, string>
  ) => {
    const currentJob = latestJobRef.current
    const completedSet = new Set(
      (currentJob.stages ?? []).filter((stage) => stage.completed_at).map((stage) => stage.stage_name)
    )
    const notes = notesOverride ?? noteDrafts
    const requestVersion = ++requestVersionRef.current
    setActiveSaveCount((count) => count + 1)
    setSaveError(null)
    try {
      const response = await updateJobStages(currentJob.id, {
        stages: stageFactory(completedSet, notes),
        rejection_stage: rejection ? rejection.stage || null : undefined,
        rejection_reason: rejection ? rejection.reason.trim() || null : undefined,
      })
      if (requestVersion === requestVersionRef.current) {
        onUpdate(toUpdatedJob(latestJobRef.current, response))
      }
      if (rejection) {
        setShowRejectionForm(false)
      }
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Failed to update job stages')
    } finally {
      setActiveSaveCount((count) => Math.max(0, count - 1))
    }
  }

  const handleStageToggle = async (stageName: StageName, completed: boolean) => {
    setPendingNoteStage(null)
    await saveUpdate((completedSet, notes) =>
      STAGE_ORDER.map((stage) => ({
        name: stage,
        completed: stage === stageName ? completed : completedSet.has(stage),
        notes: notes[stage].trim() || null,
      }))
    )
  }

  const handleNoteInputChange = (stageName: StageName, nextNotes: string) => {
    if (!completedStages.has(stageName)) {
      return
    }
    setNoteDrafts((previous) => ({ ...previous, [stageName]: nextNotes }))
    setPendingNoteStage(stageName)
  }

  const handleMarkRejected = async () => {
    if (!rejectionStage) {
      return
    }
    await saveUpdate(
      (completedSet, notes) =>
        STAGE_ORDER.map((stage) => ({
          name: stage,
          completed: completedSet.has(stage),
          notes: notes[stage].trim() || null,
        })),
      { stage: rejectionStage, reason: rejectionReason }
    )
  }

  const handleCancelRejection = () => {
    setRejectionStage(job.rejection_stage ?? '')
    setRejectionReason(job.rejection_reason ?? '')
    setShowRejectionForm(false)
  }

  useEffect(() => {
    if (!pendingNoteStage || !completedStages.has(pendingNoteStage)) {
      return
    }

    const timeout = setTimeout(() => {
      const runNoteSave = async () => {
        const currentJob = latestJobRef.current
        const completedSet = new Set(
          (currentJob.stages ?? []).filter((stage) => stage.completed_at).map((stage) => stage.stage_name)
        )
        const notesSnapshot = { ...noteDrafts }
        const requestVersion = ++requestVersionRef.current

        setActiveSaveCount((count) => count + 1)
        setSaveError(null)
        try {
          const response = await updateJobStages(currentJob.id, {
            stages: STAGE_ORDER.map((stage) => ({
              name: stage,
              completed: completedSet.has(stage),
              notes: notesSnapshot[stage].trim() || null,
            })),
          })
          if (requestVersion === requestVersionRef.current) {
            onUpdate(toUpdatedJob(latestJobRef.current, response))
          }
        } catch (error) {
          setSaveError(error instanceof Error ? error.message : 'Failed to update job stages')
        } finally {
          setActiveSaveCount((count) => Math.max(0, count - 1))
        }
      }

      void runNoteSave()
      setPendingNoteStage(null)
    }, 500)

    return () => clearTimeout(timeout)
  }, [completedStages, noteDrafts, onUpdate, pendingNoteStage])

  return (
    <Card>
      <CardHeader className="py-3">
        <button
          type="button"
          onClick={() => setIsExpanded((previous) => !previous)}
          className="flex w-full items-center justify-between text-left"
          aria-expanded={isExpanded}
        >
          <CardTitle className="text-lg">Stage Progress</CardTitle>
          {isExpanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
        </button>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-4">
          {STAGE_ORDER.map((stageName) => {
            const stage = (job.stages ?? []).find((item) => item.stage_name === stageName && item.completed_at)
            const isCompleted = completedStages.has(stageName)
            const stageId = `stage-${job.id}-${stageName}`
            const notesId = `${stageId}-notes`

            return (
              <div key={stageName} className="space-y-2 rounded-md border p-3">
                <div className="flex items-center gap-2">
                  <input
                    id={stageId}
                    type="checkbox"
                    checked={isCompleted}
                    disabled={isSaving}
                    onChange={(event) => handleStageToggle(stageName, event.target.checked)}
                    className="h-4 w-4 rounded border-input"
                  />
                  <Label htmlFor={stageId} className="font-medium">
                    {STAGE_LABELS[stageName]}
                    {stage?.completed_at ? (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {new Date(stage.completed_at).toLocaleString()}
                      </span>
                    ) : null}
                  </Label>
                </div>

                {isCompleted ? (
                  <Textarea
                    id={notesId}
                    value={noteDrafts[stageName]}
                    placeholder="Add notes..."
                    onChange={(event) => handleNoteInputChange(stageName, event.target.value)}
                    rows={2}
                  />
                ) : null}
              </div>
            )
          })}

          <div className="border-t pt-3">
            {job.status === 'rejected' && !showRejectionForm ? (
              <div className="space-y-2 text-sm">
                <p className="font-semibold text-destructive">
                  Rejected at: {job.rejection_stage ? STAGE_LABELS[job.rejection_stage] : 'Unknown'}
                </p>
                {job.rejection_reason ? <p className="text-muted-foreground">{job.rejection_reason}</p> : null}
                <Button variant="outline" size="sm" onClick={() => setShowRejectionForm(true)} disabled={isSaving}>
                  Edit Rejection
                </Button>
              </div>
            ) : !showRejectionForm ? (
              <Button variant="outline" size="sm" onClick={() => setShowRejectionForm(true)} disabled={isSaving}>
                Mark as Rejected
              </Button>
            ) : (
              <div className="space-y-3 rounded-md border p-3">
                <p className="text-sm font-medium">Rejected at stage</p>
                <div className="flex flex-wrap gap-3">
                  {STAGE_ORDER.map((stageName) => (
                    <label key={stageName} className="flex items-center gap-1 text-sm">
                      <input
                        type="radio"
                        name={`rejection-stage-${job.id}`}
                        value={stageName}
                        checked={rejectionStage === stageName}
                        disabled={isSaving}
                        onChange={(event) => setRejectionStage(parseStageName(event.target.value))}
                      />
                      {STAGE_LABELS[stageName]}
                    </label>
                  ))}
                </div>

                <div className="space-y-1">
                  <Label htmlFor={`rejection-reason-${job.id}`}>Reason (optional)</Label>
                  <Input
                    id={`rejection-reason-${job.id}`}
                    value={rejectionReason}
                    disabled={isSaving}
                    onChange={(event) => setRejectionReason(event.target.value)}
                    placeholder="e.g. Failed technical assessment"
                  />
                </div>

                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleCancelRejection}
                    disabled={isSaving}
                  >
                    Cancel
                  </Button>
                  <Button size="sm" onClick={handleMarkRejected} disabled={isSaving || !rejectionStage}>
                    {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Mark as Rejected
                  </Button>
                </div>
              </div>
            )}
          </div>

          {saveError ? (
            <p className="text-sm text-destructive" role="alert" aria-live="polite">
              {saveError}
            </p>
          ) : null}
        </CardContent>
      )}
    </Card>
  )
}
