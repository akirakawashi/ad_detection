import { useEffect, useState } from 'react'
import { listRuns } from '../api'
import { ErrorBanner, EmptyState } from '../components/common/Feedback'
import { PageHeader } from '../components/common/PageHeader'
import { RunsSkeleton } from '../components/common/Skeletons'
import { statusLabel } from '../pipeline'
import { navigate } from '../routing'
import type { PipelineRun } from '../types'
import { formatDuration } from '../utils/formatters'

export function RunsPage() {
  const [runs, setRuns] = useState<PipelineRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let disposed = false
    const load = () => {
      listRuns()
        .then((result) => {
          if (!disposed) setRuns(result.items)
        })
        .catch((reason) => {
          if (!disposed) setError(String(reason))
        })
        .finally(() => {
          if (!disposed) setLoading(false)
        })
    }
    load()
    const interval = window.setInterval(load, 5000)
    return () => {
      disposed = true
      window.clearInterval(interval)
    }
  }, [])

  return (
    <div className="page">
      <PageHeader
        eyebrow="Архив"
        title="Обработанные видео"
        actions={
          <button className="primary" onClick={() => navigate('/runs/new')}>
            Добавить видео
          </button>
        }
      />
      {loading && <RunsSkeleton />}
      {error && <ErrorBanner text={error} />}
      {!loading && !runs.length && (
        <EmptyState
          text="Здесь пока нет обработанных видео."
          action={
            <button className="primary" onClick={() => navigate('/runs/new')}>
              Добавить первое видео
            </button>
          }
        />
      )}
      <div className="runs-grid">
        {runs.map((run) => (
          <button
            className="run-card"
            key={run.run_id}
            onClick={() => navigate(`/runs/${run.run_id}`)}
          >
            <div className="run-preview">
              <span>{run.status === 'completed' ? '▶' : '···'}</span>
            </div>
            <div className="run-copy">
              <div className={`status status-${run.status}`}>
                {statusLabel(run.status)}
              </div>
              <h3>{run.source_name}</h3>
              <p>{new Date(run.created_at).toLocaleString('ru-RU')}</p>
              <div className="run-meta">
                <span>{formatDuration(run.duration_sec)}</span>
                <span>{run.progress}%</span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
