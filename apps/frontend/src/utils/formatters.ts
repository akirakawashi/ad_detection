export function formatDuration(value: number | null) {
  if (!value) return '—'
  const minutes = Math.floor(value / 60)
  const seconds = Math.round(value % 60)
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

export function formatBytes(value: number) {
  if (value < 1024 ** 2) return `${Math.round(value / 1024)} KB`
  return `${(value / 1024 ** 2).toFixed(1)} MB`
}

export function formatNumber(value: number | undefined) {
  return value === undefined
    ? '—'
    : new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(value)
}
