/**
 * The comparison board's routes — `backend/app/routers/compare.py`.
 *
 * Types here are deliberately explicit about `null`. A row with no flood extent
 * because routing is unavailable is not a row with zero flood extent, and the
 * board must be able to draw the difference.
 */
import { http } from './client'
import type { Geometry } from './types'

/** One axis row. `delta` is `b - a`, already signed by the backend. */
export interface ComparisonAxis {
  key: string
  label: string
  unit: string
  a: number | null
  b: number | null
  delta: number | null
  /** `lower-better` | `higher-better` | null when the row is context only. */
  direction: 'lower-better' | 'higher-better' | null
  /** False for context applied to both, such as the tide. */
  comparable: boolean
  note: string
}

export interface ComparisonWindDirection {
  pathLengthM: number | null
  firstObstructionMeanM: number | null
  entryEdge: string | null
  blocked: boolean | null
}

export interface ComparisonWind {
  status: string
  directions: Record<string, ComparisonWindDirection>
  /** Headline first-obstruction height (NE), in metres. */
  firstObstructionMeanM: number | null
  corridor: { type: 'LineString'; coordinates: number[][] } | null
  corridorDirection?: string
  warning?: string
  limitation?: string
  reason?: string
}

export interface ComparisonSchemeMetrics {
  drainageDeficitM3: number
  runoffM3: number
  wetAreaHa: number
  floodAreaHa: number | null
  heatIndex: number
  greenWaterAreaM2: number
  greenWaterHa: number
  imperviousShare: number
  storageCapacityM3: number
  applied: Array<Record<string, unknown>>
  skipped: Array<Record<string, unknown>>
}

export interface ComparisonScheme {
  key: 'a' | 'b'
  label: string
  planIds: string[]
  metrics: ComparisonSchemeMetrics
  wind: ComparisonWind
}

export interface ComparisonResult {
  sceneId: string
  status: string
  warning: string
  inputs: {
    rainfallMm: number
    temperatureC: number
    tideState: string
    tide: { state: string; label: string; tailwaterM: number; source: string; active: boolean }
  }
  schemes: { a: ComparisonScheme; b: ComparisonScheme }
  axes: ComparisonAxis[]
  /** Always null. The absence is the product decision, not a missing feature. */
  combinedScore: null
  whyNoCombinedScore: string
  notes: string[]
}

export interface ComparisonSideInput {
  planIds: string[]
  label: string
}

/** `POST /scenes/{id}/compare-schemes` — two schemes, five axes, no verdict. */
export async function fetchComparison(
  sceneId: string,
  body: {
    a: ComparisonSideInput
    b: ComparisonSideInput
    rainfallMm: number
    temperatureC: number
    tideState: string
  },
): Promise<ComparisonResult> {
  const { data } = await http.post<ComparisonResult>(
    `/scenes/${sceneId}/compare-schemes`,
    body,
  )
  return data
}

export interface SensitivityRow {
  label: string
  rainfallMm: number
  unstoredM3: number
}

export interface SensitivityResult {
  sceneId: string
  status: string
  warning: string
  assumption: string
  spread: number
  rows: SensitivityRow[]
  swingM3: number
  driver: string
  planIds: string[]
}

/** `POST /scenes/{id}/sensitivity` — one assumption moved, three ledger readings. */
export async function fetchSensitivity(
  sceneId: string,
  body: { planIds: string[]; rainfallMm: number; spread?: number },
): Promise<SensitivityResult> {
  const { data } = await http.post<SensitivityResult>(
    `/scenes/${sceneId}/sensitivity`,
    body,
  )
  return data
}

export interface WindDiagnostic {
  sceneId: string
  status: string
  warning: string
  direction: string
  inflowSource: string
  meanShelterIndex: number
  maxShelterIndex: number
  shelteredCells: number
  cells: number
  meanWhereSheltered: number
  overlayUrl: string
  sidecarUrl: string
  method: string
  externalCheck: string
  planIds: string[]
}

/** `POST /scenes/{id}/ventilation/diagnostic` — the corridor's geometric sidecar. */
export async function fetchWindDiagnostic(
  sceneId: string,
  body: { planIds?: string[]; direction?: string },
): Promise<WindDiagnostic> {
  const { data } = await http.post<WindDiagnostic>(
    `/scenes/${sceneId}/ventilation/diagnostic`,
    body,
  )
  return data
}

export interface StormHour {
  hour: number
  rainfallMm: number
  generatedM3: number
  storedM3: number
  drainedM3: number
  standingM3: number
  wetCells: number
  meanPoolDepthM: number
  standingMeanDepthMm: number
  overlayUrl: string | null
}

export interface StormPlayback {
  sceneId: string
  status: string
  warning: string
  hyetograph: {
    name: string
    label: string
    mmPerHour: number[]
    totalMm: number
    source: string
  }
  hours: StormHour[]
  frameNote: string
  massBalance: { identity: string; residualM3: number; enforced: boolean }
  planIds: string[]
}

/** `POST /scenes/{id}/storm/playback` — the named hourly storm as frames. */
export async function fetchStormPlayback(
  sceneId: string,
  body: { hyetographName?: string; planIds?: string[]; initialRetentionFill?: number },
): Promise<StormPlayback> {
  const { data } = await http.post<StormPlayback>(
    `/scenes/${sceneId}/storm/playback`,
    body,
  )
  return data
}

export interface WeatherReading {
  sceneId: string
  mode: 'recorded' | 'live'
  status: string
  usableAsIntensity: boolean
  rainfallMmHr: number | null
  sinceMidnightMm: number | null
  station: string | null
  observedAt: string | null
  label: string
  source: string
  note: string
  fallbackReason: string | null
  hyetograph?: {
    name: string
    label: string
    mmPerHour: number[]
    peakHour: number
    peakMmHr: number
    totalMm: number
    source: string
  }
  recordedFallback?: WeatherReading
}

/** `GET /scenes/{id}/weather/current` — a labelled storm input. */
export async function fetchWeather(
  sceneId: string,
  mode: 'recorded' | 'live' = 'recorded',
): Promise<WeatherReading> {
  const { data } = await http.get<WeatherReading>(`/scenes/${sceneId}/weather/current`, {
    params: { mode },
  })
  return data
}

/** Re-exported for callers that only need the shape of a corridor geometry. */
export type CorridorGeometry = Extract<Geometry, { type: 'LineString' }>
