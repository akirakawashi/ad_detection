import { PIPELINE_STAGES } from '../../pipeline'

interface PipelineStepsProps {
  activeStage: string
  failed: boolean
}

export function PipelineSteps({ activeStage, failed }: PipelineStepsProps) {
  const activeIndex = PIPELINE_STAGES.findIndex(
    (stage) => stage.key === activeStage,
  )
  return (
    <div className="steps">
      {PIPELINE_STAGES.map((stage, index) => {
        const done = activeIndex !== -1 && index < activeIndex
        const active = stage.key === activeStage
        const failedActive = failed && active
        return (
          <div
            key={stage.key}
            className={[
              'step',
              done ? 'done' : '',
              active ? 'active' : '',
              failedActive ? 'failed' : '',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            <span />
            <div>
              <strong>{stage.label}</strong>
              <small>{stage.description}</small>
            </div>
          </div>
        )
      })}
    </div>
  )
}
