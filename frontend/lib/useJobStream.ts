'use client';

import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const STEP_ORDER = ['scraping', 'parsing', 'tailoring', 'compiling'] as const;
export type PipelineStep = (typeof STEP_ORDER)[number];
export type StepState = 'pending' | 'running' | 'completed' | 'failed';

type StepStateMap = Record<PipelineStep, StepState>;

const DEFAULT_STEP_STATES: StepStateMap = {
  scraping: 'pending',
  parsing: 'pending',
  tailoring: 'pending',
  compiling: 'pending',
};

interface StreamEventPayload {
  type: string;
  step?: string;
  error?: string | null;
}

function isPipelineStep(step: string | undefined): step is PipelineStep {
  return !!step && STEP_ORDER.includes(step as PipelineStep);
}

export function useJobStream(
  jobId: number | null,
  enabled: boolean,
  onTerminalEvent?: () => void,
) {
  const [stepStates, setStepStates] = useState<StepStateMap>(DEFAULT_STEP_STATES);
  const [lastEventType, setLastEventType] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!enabled || !jobId) {
      return;
    }

    const stream = new EventSource(`${API_BASE}/jobs/${jobId}/stream`);
    const terminalEvents = new Set(['pipeline_completed', 'pipeline_failed']);

    const handleEvent = (evt: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(evt.data) as StreamEventPayload;
        setLastEventType(payload.type);

        if (payload.error) {
          setError(payload.error);
        }

        if (isPipelineStep(payload.step)) {
          const step = payload.step;
          setStepStates((previous) => {
            const next = { ...previous };
            if (payload.type === 'step_started') {
              next[step] = 'running';
            } else if (payload.type === 'step_completed') {
              next[step] = 'completed';
            } else if (payload.type === 'step_failed') {
              next[step] = 'failed';
            }
            return next;
          });
        }

        if (terminalEvents.has(payload.type)) {
          stream.close();
          onTerminalEvent?.();
        }
      } catch {
        // Ignore malformed SSE payloads.
      }
    };

    stream.onopen = () => {
      setConnected(true);
      setError(null);
    };

    stream.onerror = () => {
      setConnected(false);
    };

    const eventTypes = [
      'pipeline_started',
      'pipeline_completed',
      'pipeline_failed',
      'step_started',
      'step_completed',
      'step_failed',
      'keepalive',
    ];

    eventTypes.forEach((type) => {
      stream.addEventListener(type, handleEvent as EventListener);
    });

    return () => {
      eventTypes.forEach((type) => {
        stream.removeEventListener(type, handleEvent as EventListener);
      });
      stream.close();
    };
  }, [enabled, jobId, onTerminalEvent]);

  return {
    stepStates,
    lastEventType,
    error,
    connected,
    stepOrder: STEP_ORDER,
  };
}
