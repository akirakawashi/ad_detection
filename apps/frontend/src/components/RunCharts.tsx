import { useMemo, useState, type CSSProperties } from 'react'
import {
  Bar,
  BarChart,
  Brush,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { BrandSummary, RunTimeline } from '../types'

const BRAND_COLORS: Record<string, string> = {
  mts: '#ff4d4d',
  miranda: '#05c3a1',
  plus7: '#58a6ff',
  other: '#b8bec6',
}

const BRAND_ORDER = ['mts', 'miranda', 'plus7', 'other']
const FALLBACK_COLORS = ['#e7c84d', '#a78bfa', '#fb923c', '#22d3ee']

const tooltipStyle = {
  background: '#151515',
  border: '1px solid rgba(255,255,255,.14)',
  borderRadius: 8,
  color: '#f4f4f4',
}

interface RunChartsProps {
  brands: BrandSummary[]
  timeline: RunTimeline
  onSeek: (seconds: number) => void
}

export function RunCharts({ brands, timeline, onSeek }: RunChartsProps) {
  const [hiddenBrands, setHiddenBrands] = useState<Set<string>>(new Set())

  const availableBrands = useMemo(() => {
    const values = new Set<string>()
    brands.forEach((brand) => values.add(normalizeBrand(brand.brand)))
    timeline.points.forEach((point) =>
      values.add(normalizeBrand(point.business_brand)),
    )
    return [...values].sort(compareBrands)
  }, [brands, timeline])

  const visibleBrandKeys = useMemo(
    () => availableBrands.filter((brand) => !hiddenBrands.has(brand)),
    [availableBrands, hiddenBrands],
  )

  const brandRows = useMemo(
    () =>
      brands
        .map((brand) => ({
          ...brand,
          brand_key: normalizeBrand(brand.brand),
          brand_label: formatBrandLabel(brand.brand),
        }))
        .filter((brand) => !hiddenBrands.has(brand.brand_key)),
    [brands, hiddenBrands],
  )

  const timelineRows = useMemo(() => {
    const rows = new Map<number, Record<string, number>>()
    timeline.points.forEach((point) => {
      const brand = normalizeBrand(point.business_brand)
      if (hiddenBrands.has(brand)) return

      const row: Record<string, number> =
        rows.get(point.bucket_start_sec) ?? {
          time: point.bucket_start_sec,
        }
      row[brand] = (row[brand] ?? 0) + point.visibility_score
      rows.set(point.bucket_start_sec, row)
    })
    return [...rows.values()].sort(
      (first, second) => Number(first.time) - Number(second.time),
    )
  }, [hiddenBrands, timeline])

  const pieData = brandRows.map((brand) => ({
    name: brand.brand_label,
    brand_key: brand.brand_key,
    value: Number(brand.video_visibility_weighted_seconds ?? 0),
  }))

  const toggleBrand = (brand: string) => {
    setHiddenBrands((current) => {
      const next = new Set(current)
      if (next.has(brand)) {
        next.delete(brand)
      } else {
        next.add(brand)
      }
      return next
    })
  }

  return (
    <>
      <section className="charts-toolbar" aria-label="Фильтр брендов">
        <span>Бренды на графиках</span>
        <div className="brand-filter">
          {availableBrands.map((brand) => {
            const hidden = hiddenBrands.has(brand)
            return (
              <button
                className={`brand-toggle${hidden ? ' hidden' : ''}`}
                key={brand}
                onClick={() => toggleBrand(brand)}
                style={
                  { '--brand-color': getBrandColor(brand) } as CSSProperties
                }
                type="button"
                aria-pressed={!hidden}
              >
                <span />
                {formatBrandLabel(brand)}
              </button>
            )
          })}
        </div>
      </section>

      <div className="charts-grid">
      <section className="panel chart-card">
        <header>
          <h3>Объекты по брендам</h3>
          <p>Количество уникальных рекламных объектов</p>
        </header>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={brandRows}>
            <CartesianGrid stroke="rgba(255,255,255,.08)" vertical={false} />
            <XAxis dataKey="brand_label" stroke="#8d9298" />
            <YAxis allowDecimals={false} stroke="#8d9298" />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey="object_count" radius={[6, 6, 0, 0]}>
              {brandRows.map((entry) => (
                <Cell
                  key={entry.brand_key}
                  fill={getBrandColor(entry.brand_key)}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </section>

      <section className="panel chart-card">
        <header>
          <h3>Доля видимости</h3>
          <p>Взвешенное время присутствия брендов</p>
        </header>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pieData}
              dataKey="value"
              nameKey="name"
              innerRadius="55%"
              outerRadius="82%"
              paddingAngle={2}
            >
              {pieData.map((entry) => (
                <Cell
                  key={entry.brand_key}
                  fill={getBrandColor(entry.brand_key)}
                />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
          </PieChart>
        </ResponsiveContainer>
      </section>

      <section className="panel chart-card timeline-chart">
        <header>
          <h3>Timeline видимости</h3>
          <p>Нажмите на столбец, чтобы перейти к моменту видео</p>
        </header>
        <ResponsiveContainer width="100%" height={340}>
          <BarChart
            data={timelineRows}
            onClick={(state) => {
              if (
                state &&
                typeof state === 'object' &&
                'activeLabel' in state
              ) {
                const value = state.activeLabel
                if (value !== undefined) onSeek(Number(value))
              }
            }}
          >
            <CartesianGrid stroke="rgba(255,255,255,.08)" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="#8d9298"
              tickFormatter={(value) => `${value}s`}
            />
            <YAxis stroke="#8d9298" />
            <Tooltip
              contentStyle={tooltipStyle}
              labelFormatter={(value) => `${value} сек.`}
            />
            {visibleBrandKeys.map((brand) => (
              <Bar
                key={brand}
                dataKey={brand}
                stackId="visibility"
                fill={getBrandColor(brand)}
              />
            ))}
            <Brush dataKey="time" height={24} stroke="#05c3a1" />
          </BarChart>
        </ResponsiveContainer>
      </section>
    </div>
    </>
  )
}

function normalizeBrand(value: string | null | undefined): string {
  return (value || 'other').toLowerCase()
}

function compareBrands(first: string, second: string): number {
  const firstIndex = BRAND_ORDER.indexOf(first)
  const secondIndex = BRAND_ORDER.indexOf(second)
  const firstOrder = firstIndex === -1 ? BRAND_ORDER.length : firstIndex
  const secondOrder = secondIndex === -1 ? BRAND_ORDER.length : secondIndex
  if (firstOrder !== secondOrder) return firstOrder - secondOrder
  return first.localeCompare(second)
}

function formatBrandLabel(brand: string): string {
  return brand.toUpperCase()
}

function getBrandColor(brand: string): string {
  if (BRAND_COLORS[brand]) return BRAND_COLORS[brand]
  const hash = [...brand].reduce(
    (result, character) => result + character.charCodeAt(0),
    0,
  )
  return FALLBACK_COLORS[hash % FALLBACK_COLORS.length]
}
