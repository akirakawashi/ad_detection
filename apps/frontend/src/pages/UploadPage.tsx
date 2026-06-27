import { useState } from 'react'
import { completeUpload, createRun, uploadVideo } from '../api'
import { ErrorBanner } from '../components/common/Feedback'
import { FileCard } from '../components/common/FileCard'
import { InfinityLoader } from '../components/common/LoadingIndicators'
import { PageHeader } from '../components/common/PageHeader'
import { ProgressBar } from '../components/common/ProgressBar'
import { navigate } from '../routing'

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [progress, setProgress] = useState(0)
  const [busy, setBusy] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectFile = (nextFile: File | null) => {
    if (busy) return
    setFile(nextFile)
    setProgress(0)
    setError(null)
  }

  const startUpload = async () => {
    if (!file) return
    setBusy(true)
    setProgress(0)
    setError(null)
    try {
      const run = await createRun(file)
      await uploadVideo(run.upload, file, setProgress)
      await completeUpload(run.run_id)
      navigate(`/runs/${run.run_id}`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
      setBusy(false)
    }
  }

  return (
    <div className="page narrow-page">
      <PageHeader
        eyebrow="Загрузка"
        title="Добавьте видео маршрута"
        description="Выберите файл или перетащите его в окно. Мы загрузим видео и сразу запустим анализ."
        actions={
          <button className="secondary" onClick={() => navigate('/runs')}>
            В архив
          </button>
        }
      />
      <section
        className={`upload-panel${dragActive ? ' drag-active' : ''}${
          busy ? ' busy' : ''
        }`}
        onDragEnter={(event) => {
          event.preventDefault()
          setDragActive(true)
        }}
        onDragOver={(event) => {
          event.preventDefault()
          setDragActive(true)
        }}
        onDragLeave={(event) => {
          event.preventDefault()
          setDragActive(false)
        }}
        onDrop={(event) => {
          event.preventDefault()
          setDragActive(false)
          selectFile(event.dataTransfer.files[0] ?? null)
        }}
      >
        <div className="upload-icon">↑</div>
        <h2>{file ? 'Файл выбран' : 'Перетащите видео сюда'}</h2>
        <p>
          {file
            ? 'Если всё верно, можно начинать анализ.'
            : 'Подойдут MP4, MOV, MKV и WebM'}
        </p>

        {file && <FileCard file={file} />}

        <div className="upload-actions">
          <label className="secondary file-button">
            {file ? 'Выбрать другое' : 'Выбрать видео'}
            <input
              type="file"
              accept="video/*,.mkv"
              disabled={busy}
              onChange={(event) => selectFile(event.target.files?.[0] ?? null)}
            />
          </label>
          {file && !busy && (
            <button className="ghost-button" onClick={() => selectFile(null)}>
              Убрать файл
            </button>
          )}
        </div>

        {busy && (
          <div className="upload-progress-card">
            <InfinityLoader compact />
            <div>
              <h3>Загружаем видео</h3>
              <p>
                Сохраняем исходный файл. Если ролик большой, это может занять
                пару минут.
              </p>
            </div>
            <ProgressBar progress={progress} label="Файл загружается" animated />
          </div>
        )}
        {error && <ErrorBanner text={error} />}
        <button
          className="primary action-button"
          disabled={!file || busy}
          onClick={() => void startUpload()}
        >
          {busy ? 'Загружаем…' : 'Начать анализ'}
        </button>
      </section>
    </div>
  )
}
