/**
 * The comparison board's state.
 *
 * A is a snapshot the user pins; B is whatever is selected in the project
 * catalog right now. That asymmetry is the demo: build one scheme, pin it as A,
 * toggle to the next scheme, and B follows the live selection while A stays the
 * thing being compared against.
 *
 * The store also owns the two sidecars that share the board's inputs — the
 * rainfall sensitivity strip and the geometric wind diagnostic — so a reader
 * does not have to guess which scheme those numbers describe.
 */
import { create } from 'zustand'

import {
  fetchComparison,
  fetchSensitivity,
  fetchWindDiagnostic,
  type ComparisonResult,
  type SensitivityResult,
  type WindDiagnostic,
} from '@/api/comparisonApi'
import { errorMessage } from '@/api/client'
import { useSceneStore } from '@/state/sceneStore'

export interface ComparisonState {
  /** The pinned A scheme. Empty means "today, no projects". */
  aPlanIds: string[]
  aLabel: string
  result: ComparisonResult | null
  loading: boolean
  error: string | null
  sensitivity: SensitivityResult | null
  sensitivityLoading: boolean
  diagnostic: WindDiagnostic | null
  diagnosticLoading: boolean
  setA: (planIds: string[], label: string) => void
  compare: (
    sceneId: string,
    b: { planIds: string[]; label: string },
    env: {
      rainfallMm: number
      temperatureC: number
      tideState: string
      windFrom?: string
      windSeason?: 'annual' | 'summer' | 'winter'
      windHeightM?: 500 | 300 | 200
      windPreset?: 'pland' | 'signal3' | 'signal8' | 'signal10' | 'manual'
      windSpeedMps?: number | null
    },
  ) => Promise<void>
  runSensitivity: (sceneId: string, planIds: string[], rainfallMm: number) => Promise<void>
  runDiagnostic: (sceneId: string, planIds: string[]) => Promise<void>
  clearDiagnostic: () => void
  clearError: () => void
}

export const useComparisonStore = create<ComparisonState>((set, get) => ({
  aPlanIds: [],
  aLabel: 'Today (no projects)',
  result: null,
  loading: false,
  error: null,
  sensitivity: null,
  sensitivityLoading: false,
  diagnostic: null,
  diagnosticLoading: false,

  setA: (planIds, label) => set({ aPlanIds: planIds, aLabel: label }),

  compare: async (sceneId, b, env) => {
    const { aPlanIds, aLabel } = get()
    set({ loading: true, error: null })
    try {
      const result = await fetchComparison(sceneId, {
        a: { planIds: aPlanIds, label: aLabel },
        b,
        rainfallMm: env.rainfallMm,
        temperatureC: env.temperatureC,
        tideState: env.tideState,
        windFrom: env.windFrom,
        windSeason: env.windSeason,
        windHeightM: env.windHeightM,
        windPreset: env.windPreset,
        windSpeedMps: env.windSpeedMps,
      })
      set({ result, loading: false })
      // The corridor is map state, so it goes to the scene store the viewer
      // reads. Clearing the diagnostic with it is deliberate: a shelter raster
      // from the previous scheme beside a new scheme's corridor would be two
      // different massings on screen at once.
      useSceneStore.getState().setWindCorridor(result.schemes.b.wind.corridor)
      useSceneStore.getState().setWindDiagnosticUrl(null)
      set({ diagnostic: null, sensitivity: null })
    } catch (error) {
      set({ loading: false, error: errorMessage(error) })
    }
  },

  runSensitivity: async (sceneId, planIds, rainfallMm) => {
    set({ sensitivityLoading: true, error: null })
    try {
      const sensitivity = await fetchSensitivity(sceneId, { planIds, rainfallMm })
      set({ sensitivity, sensitivityLoading: false })
    } catch (error) {
      set({ sensitivityLoading: false, error: errorMessage(error) })
    }
  },

  runDiagnostic: async (sceneId, planIds) => {
    set({ diagnosticLoading: true, error: null })
    try {
      const diagnostic = await fetchWindDiagnostic(sceneId, { planIds, direction: 'NE' })
      set({ diagnostic, diagnosticLoading: false })
      useSceneStore.getState().setWindDiagnosticUrl(diagnostic.overlayUrl)
      useSceneStore.getState().setLayers({ wind: true })
    } catch (error) {
      set({ diagnosticLoading: false, error: errorMessage(error) })
    }
  },

  clearDiagnostic: () => {
    useSceneStore.getState().setWindDiagnosticUrl(null)
    set({ diagnostic: null })
  },

  clearError: () => set({ error: null }),
}))
