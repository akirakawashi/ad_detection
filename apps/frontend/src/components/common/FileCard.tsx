import { formatBytes } from '../../utils/formatters'

export function FileCard({ file }: { file: File }) {
  return (
    <div className="file-card">
      <div className="file-card-icon">▶</div>
      <div>
        <strong>{file.name}</strong>
        <span>
          {formatBytes(file.size)} · {file.type || 'video'}
        </span>
      </div>
    </div>
  )
}
