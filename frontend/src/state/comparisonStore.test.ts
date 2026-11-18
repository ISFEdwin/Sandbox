/**
 * The comparison store's two jobs the demo depends on.
 *
 * 1. A board's corridor becomes map state, and a new board clears the previous
 *    scheme's shelter raster — otherwise two massings would be on screen at once.
 * 2. The sidecars (sensitivity, shelter) are stored with the same inputs, so the
 *    panel can never show a number for a scheme it is not comparing.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ComparisonResult, SensitivityResult, WindDiagnostic } from '@/api/comparisonApi'
import { DEFAULT_LAYERS, useSceneStore } from '@/state/sceneStore'

const result = {
  sceneId: 's1',
  status: 'SCREENING_COMPARISON_NOT_A_VERDICT',
  warning: 'screening',
  inputs: {
    rainfallMm: 50, temperatureC: 30, tideState: 'low',
    tide: { state: 'low', label: 'Low', tailwaterM: 0, source: 'x', active: false },
  },
  schemes: {
    a: {
      key: 'a', label: 'Today', planIds: [],
      metrics: { drainageDeficitM3: 1, runoffM3: 1, wetAreaHa: 1, floodAreaHa: 0,
        heatIndex: 0.9, greenWaterAreaM2: 1, greenWaterHa: 0.1, imperviousShare: 0.8,
        storageCapacityM3: 0, applied: [], skipped: [] },
      wind: { status: 'WIND_CORRIDOR_GEOMETRY', directions: {}, firstObstructionMeanM: 15,
        corridor: { type: 'LineString', coordinates: [[1, 2], [3, 4]] } },
    },
    b: {
      key: 'b', label: 'Scheme', planIds: ['p1'],
      metrics: { drainageDeficitM3: 2, runoffM3: 2, wetAreaHa: 2, floodAreaHa: 0,
        heatIndex: 0.8, greenWaterAreaM2: 2, greenWaterHa: 0.2, imperviousShare: 0.7,
        storageCapacityM3: 100, applied: [], skipped: [] },
      wind: { status: 'WIND_CORRIDOR_GEOMETRY', directions: {}, firstObstructionMeanM: 9,
        corridor: { type: 'LineString', coordinates: [[9, 9], [8, 8]] } },
    },
  },
  axes: [],
  combinedScore: null,
  whyNoCombinedScore: 'no score',
  notes: [],
} as unknown as ComparisonResult

const sensitivity = { rows: [], swingM3: 1, driver: 'rainfall' } as unknown as SensitivityResult
const diagnostic = {
  overlayUrl: '/static/rasters/comparison/a.png',
  meanShelterIndex: 0.4,
  maxShelterIndex: 0.9,
  direction: 'NE',
  warning: 'geometry',
} as unknown as WindDiagnostic

const fetchComparison = vi.fn(async (..._args: unknown[]) => result)
const fetchSensitivity = vi.fn(async (..._args: unknown[]) => sensitivity)
const fetchWindDiagnostic = vi.fn(async (..._args: unknown[]) => diagnostic)

vi.mock('@/api/comparisonApi', () => ({
  fetchComparison: (sceneId: string, body: unknown) => fetchComparison(sceneId, body),
  fetchSensitivity: (sceneId: string, body: unknown) => fetchSensitivity(sceneId, body),
  fetchWindDiagnostic: (sceneId: string, body: unknown) => fetchWindDiagnostic(sceneId, body),
}))

// Imported after the mock so the store binds to the mocked module.
const { useComparisonStore } = await import('@/state/comparisonStore')

beforeEach(() => {
  useComparisonStore.setState({
    aPlanIds: [], aLabel: 'Today (no projects)', result: null, loading: false,
    error: null, sensitivity: null, sensitivityLoading: false, diagnostic: null,
    diagnosticLoading: false,
  })
  useSceneStore.setState({
    windCorridor: null,
    windDiagnosticUrl: null,
    layers: { ...DEFAULT_LAYERS },
  })
})

describe('the comparison store', () => {
  it('puts the board on screen and its corridor on the map', async () => {
    await useComparisonStore.getState().compare(
      's1', { planIds: ['p1'], label: 'Scheme' },
      { rainfallMm: 50, temperatureC: 30, tideState: 'low' },
    )
    const state = useComparisonStore.getState()
    expect(state.result?.combinedScore).toBeNull()
    expect(fetchComparison).toHaveBeenCalledOnce()
    // B is the live selection, so B's corridor is the one drawn.
    expect(useSceneStore.getState().windCorridor).toEqual(result.schemes.b.wind.corridor)
    expect(useSceneStore.getState().layers.wind).toBe(true)
  })

  it('clears the previous scheme\'s shelter raster when a new board arrives', async () => {
    useSceneStore.setState({ windDiagnosticUrl: '/static/rasters/comparison/old.png' })
    useComparisonStore.setState({ diagnostic })
    await useComparisonStore.getState().compare(
      's1', { planIds: [], label: 'Today' },
      { rainfallMm: 50, temperatureC: 30, tideState: 'low' },
    )
    expect(useSceneStore.getState().windDiagnosticUrl).toBeNull()
    expect(useComparisonStore.getState().diagnostic).toBeNull()
  })

  it('shows the shelter raster and switches the wind layer on', async () => {
    await useComparisonStore.getState().runDiagnostic('s1', ['p1'])
    expect(useSceneStore.getState().windDiagnosticUrl).toBe(diagnostic.overlayUrl)
    expect(useSceneStore.getState().layers.wind).toBe(true)
  })

  it('keeps the sensitivity reading beside the same inputs', async () => {
    await useComparisonStore.getState().runSensitivity('s1', ['p1'], 50)
    expect(useComparisonStore.getState().sensitivity).toBe(sensitivity)
    expect(fetchSensitivity).toHaveBeenCalledWith('s1', { planIds: ['p1'], rainfallMm: 50 })
  })
})
