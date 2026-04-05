import { JobStageResponse, StageName } from "@/lib/api"
import { cn } from "@/lib/utils"

const STAGE_ORDER = ["applied", "oa", "interview", "offer"] as const satisfies readonly StageName[]

const STAGE_LABELS: Record<StageName, string> = {
  applied: "Applied",
  oa: "OA",
  interview: "Interview",
  offer: "Offer",
}

interface StageProgressProps {
  stages?: JobStageResponse[]
  className?: string
}

export function StageProgress({ stages = [], className }: StageProgressProps) {
  const completedStages = new Set(
    stages.filter((stage) => Boolean(stage.completed_at)).map((stage) => stage.stage_name)
  )

  const nextStage = STAGE_ORDER.find((stage) => !completedStages.has(stage))

  return (
    <div className={cn("flex flex-wrap items-center gap-1 text-xs text-muted-foreground", className)}>
      {STAGE_ORDER.map((stage, index) => {
        const symbol = completedStages.has(stage)
          ? "✓"
          : stage === nextStage
            ? "⏳"
            : "○"

        return (
          <div key={stage} className="flex items-center gap-1">
            <span className="font-medium leading-none">{symbol}</span>
            <span className="leading-none">{STAGE_LABELS[stage]}</span>
            {index < STAGE_ORDER.length - 1 ? <span className="mx-1 text-muted-foreground/70">→</span> : null}
          </div>
        )
      })}
    </div>
  )
}
