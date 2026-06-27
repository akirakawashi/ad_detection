export const PIPELINE_STAGES = [
  {
    key: 'queued',
    label: 'В очереди',
    description: 'Файл загружен в хранилище. Ждём, когда освободится обработчик.',
  },
  {
    key: 'preparing',
    label: 'Подготовка',
    description: 'Видео обрабатывается, проверяем длительность, FPS, размер кадра и т. д.',
  },
  {
    key: 'detection',
    label: 'Детекция',
    description: 'Анализ видео - ищем рекламные конструкции в кадрах.',
  },
  {
    key: 'tracking',
    label: 'Трекинг',
    description: 'Собираем трек по видеопотоку и объединяем с объектами на видео.',
  },
  {
    key: 'classification',
    label: 'Классификация',
    description: 'Лучшие фрагменты отдаем классификатору и определяем бренд.',
  },
  {
    key: 'aggregation',
    label: 'Расчёт метрик',
    description: 'Считаем количество объектов, заметность и уверенность по брендам.',
  },
  {
    key: 'rendering',
    label: 'Подготовка просмотра',
    description: 'Готовим видео с разметкой и данные для графиков.',
  },
  {
    key: 'uploading_artifacts',
    label: 'Сохранение результата',
    description: 'Сохраняем таблицы, кадры объектов, графики и итоговое видео.',
  },
]

export function statusLabel(status: string) {
  return (
    {
      uploading: 'Загружается',
      queued: 'В очереди',
      processing: 'Идёт анализ',
      completed: 'Готово',
      processing_failed: 'Ошибка анализа',
    }[status] ?? status
  )
}

export function stageLabel(stage: string) {
  if (stage === 'completed') return 'Готово'
  return PIPELINE_STAGES.find((item) => item.key === stage)?.label ?? stage
}

export function stageDescription(stage: string) {
  if (stage === 'completed') return 'Готово. Можно смотреть видео и графики.'
  return (
    PIPELINE_STAGES.find((item) => item.key === stage)?.description ??
    'Ждём обновление статуса.'
  )
}
