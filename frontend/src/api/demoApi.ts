/**
 * The three demo reads: a named storm, a labelled gauge, the ledger at ±20%.
 *
 * None of them invent a model. The storm is the hourly route, the gauge is
 * an HKO observation written into the run's existing inputs, and the strip
 * is `storage_ledger` three times.
 */
import { http } from './client'
import type { TideState } from './types'

export interface GaugeReading {
  mode: 'live' | 'recorded'
  rainfallMm: number
  place: string
  observedAt: string | null
  source: string
  sourceUrl: string | null
  tideState: TideState | null
  tideHeightM: number | null
  tidePlace: string | null
  tideObservedAt: string | null
  tideSource: string | null
  note: string | null
  fallback: string | null
  label: string
}

export interface StormFrame {
  hour: number
  rainfallMm: number
  standingM3: number | null
  url: string
}

export interface HourlyStorm {
  hours: number
  screeningLine: string
  warning: string
  hyetograph: { name: string; label: string; totalMm: number; source: string }
  massBalance: { enforced: boolean; residualM3: number }
  frames: StormFrame[]
}

export interface SensitivityPoint {
  name: 'low' | 'baseline' | 'high'
  scale: number
  rainfallMm: number
  unstoredM3: number
}

export interface SensitivityReport {
  assumption: string
  factor: number
  baselineRainfallMm: number
  points: SensitivityPoint[]
  sentence: string
  source: string
}

export async function fetchHourlyStorm(
  sceneId: string,
  hyetographName = 'hko_2023_09_07',
): Promise<HourlyStorm> {
  const { data } = await http.get<HourlyStorm>(`/scenes/${sceneId}/drainage/hourly`, {
    params: { hyetographName },
    timeout: 60_000,
  })
  return data
}

export async function fetchGauge(
  sceneId: string,
  mode: 'live' | 'recorded',
): Promise<GaugeReading> {
  const { data } = await http.get<GaugeReading>(`/scenes/${sceneId}/gauge`, {
    params: { mode },
    timeout: 20_000,
  })
  return data
}

export async function fetchSensitivity(
  sceneId: string,
  rainfallMm: number,
): Promise<SensitivityReport> {
  const { data } = await http.get<SensitivityReport>(
    `/scenes/${sceneId}/ledger/sensitivity`,
    { params: { rainfallMm, factor: 0.2 } },
  )
  return data
}
