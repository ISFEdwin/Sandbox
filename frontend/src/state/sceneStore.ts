/**
 * Scene state — the frontend's source of truth (CLAUDE.md: "State | Zustand
 * stores — source of truth").
 *
 * The render layer reads from here and never fetches (CLAUDE.md: "The rendering
 * layer must not fetch data itself"). Data flows API -> State -> View.
 */
import { create } from 'zustand'

import { fetchWindHeat, getScene, getTerrain, runSimulation, type WindHeatReading } from '@/api/sceneApi'
import { errorMessage } from '@/api/client'
import type {
  EnvParams,
  LayerVisibility,
  RunResult,
  Scene,
  TerrainMeta,
  ViewMode,
} from '@/api/types'

/**
 * The minimum a payload must carry to be treated as a scene.
 *
 * Deliberately shallow. The point is not to re-validate the whole contract -- that
 * is the schema layer's job -- it is to stop an unreadable object reaching the panels,
 * because a throw inside a React render unmounts the tree and the user gets a white
 * page instead of a sentence.
 */
function isScene(value: unknown): value is Scene {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<Scene>
  const centre = candidate.center?.coordinates
  return (
    Array.isArray(centre) &&
    centre.length >= 2 &&
    centre.every((n) => typeof n === 'number') &&
    !!candidate.bbox &&
    !!candidate.defaultCamera
  )
}

/**
 * Slider defaults, used when the scene carries no `envParams` of its own.
 *
 * Rainfall is expressed as *intensity* (mm/hr) plus a *duration* (hours); the
 * two multiply to the storm-total depth the SCS-CN equation actually consumes.
 * 50 mm/hr × 1 h = 50 mm total — a routine-to-heavy HK storm, well above the
 * ~20 mm on-site depression-storage floor so it still produces visible runoff
 * without reading as an extreme. 450 mm total — a 1-in-50 yr design storm —
 * remains the value the committed overlay artefacts were baked at.
 */
export const DEFAULT_RAINFALL_MMH = 50
export const DEFAULT_DURATION_HOURS = 1
export const DEFAULT_TEMPERATURE_C = 30
export const DEFAULT_TIDE_STATE = 'low' as const

export interface SceneState {
  sceneId: string
  scene: Scene | null
  terrain: TerrainMeta | null
  loading: boolean
  error: string | null
  layers: LayerVisibility
  /**
   * The latest live run, and the state of the run in flight.
   *
   * Kept in the store rather than in the panel that triggered it: the viewer
   * reads the overlay URLs from here, so the result survives a panel remount
   * and stays visible while the user orbits the sandbox.
   */
  runResult: RunResult | null
  running: boolean
  runError: string | null
  /**
   * How the scene is dressed. Session-local like `layers`, and deliberately not
   * persisted: it is a viewing preference, not a property of the study area, so
   * putting it on the scene record would make a renderer choice look like data.
   */
  viewMode: ViewMode
  /**
   * The prevailing-wind corridor currently drawn, and its optional diagnostic.
   *
   * Held here rather than in the comparison store because the viewer reads the
   * scene store; the comparison panel writes it when a board arrives. A corridor
   * is map state, not a result the panel has to keep alive.
   */
  windCorridor: {
    type: 'LineString'
    coordinates: number[][]
    properties?: {
      geometricEffects?: { labels?: string[]; at: number[] }[]
      sidecar?: { status?: string; method?: string; limitation?: string }
    }
  } | null
  windDiagnosticUrl: string | null
  /** Meteorological FROM bearing. The OpenFOAM file for this name is the channel. */
  windFrom: string
  windSeason: 'annual' | 'summer' | 'winter'
  windHeightM: 500 | 300 | 200
  /** Selected-table inlet divided by the annual 500 m inlet. 1 when they match. */
  windSpeedScale: number
  /** `pland` follows the selected PlanD table. A signal preset is an HKO onset. */
  windPreset: 'pland' | 'signal3' | 'signal8' | 'signal10' | 'manual'
  /** Set when the preset is manual. Signal presets carry their own onset. */
  windSpeedMps: number | null
  windHeat: WindHeatReading | null
  windHeatLoading: boolean
  load: (sceneId: string) => Promise<void>
  setEnvParams: (patch: Partial<EnvParams>) => void
  run: (planIds: string[] | null) => Promise<void>
  toggleLayer: (layer: keyof LayerVisibility) => void
  setLayers: (layers: Partial<LayerVisibility>) => void
  setViewMode: (mode: ViewMode) => void
  setWindCorridor: (corridor: {
    type: 'LineString'
    coordinates: number[][]
    properties?: {
      geometricEffects?: { labels?: string[]; at: number[] }[]
      sidecar?: { status?: string; method?: string; limitation?: string }
    }
  } | null) => void
  setWindDiagnosticUrl: (url: string | null) => void
  setWindFrom: (direction: string) => void
  setWindTable: (season: 'annual' | 'summer' | 'winter', heightM: 500 | 300 | 200) => void
  setWindSpeedScale: (scale: number) => void
  setWindPreset: (preset: 'pland' | 'signal3' | 'signal8' | 'signal10' | 'manual') => void
  setWindSpeedMps: (speed: number) => void
  refreshWindHeat: () => Promise<void>
  clearError: () => void
  planProjectLoading: boolean
  setPlanProjectLoading: (v: boolean) => void
}

export const DEFAULT_LAYERS: LayerVisibility = {
  boundary: true,
  // Overlays start off: they are extra context, and the study area is legible
  // without them. Interventions start on, because a scene whose plan has
  // features but shows none of them reads as a broken demo.
  wetGrid: false,
  heatmap: false,
  wind: false,
  interventions: true,
  props: true,
  realBuildings: true,
  massing25d: false,
}

export const useSceneStore = create<SceneState>((set, get) => ({
  sceneId: '',
  scene: null,
  terrain: null,
  loading: false,
  error: null,
  layers: { ...DEFAULT_LAYERS },
  viewMode: 'tactical',
  windCorridor: null,
  windDiagnosticUrl: null,
  windFrom: 'NE',
  windSeason: 'annual',
  windHeightM: 500,
  windSpeedScale: 1,
  windPreset: 'pland',
  windSpeedMps: null,
  windHeat: null,
  windHeatLoading: false,
  runResult: null,
  running: false,
  runError: null,
  planProjectLoading: false,
  setPlanProjectLoading: (v) => set({ planProjectLoading: v }),

  load: async (sceneId) => {
    set({ loading: true, error: null, sceneId })
    try {
      // The scene is the anchor: terrain is fetched alongside it because the
      // viewer cannot initialise without both, and a half-loaded viewer is
      // worse than a slightly slower one.
      const [scene, terrain] = await Promise.all([getScene(sceneId), getTerrain(sceneId)])
      // Refuse a payload that is not a scene, rather than storing it.
      //
      // Measured: a 200 whose body lacked the expected fields left the app with an
      // empty `#root` — a completely blank page, no message, no console error worth
      // reading. The panels then read `scene.center.coordinates` and the throw inside
      // a render unmounts the whole tree. A proxy serving the wrong body, or a
      // contract drift, would present to a user exactly like the app not loading.
      if (!isScene(scene)) {
        set({
          error:
            'The server returned a scene record this app cannot read (missing centre, ' +
            'bbox or default camera). Check that the API and frontend versions match.',
          loading: false,
        })
        return
      }
      set({ scene, terrain, loading: false, windCorridor: null, windDiagnosticUrl: null })
    } catch (error) {
      set({ error: errorMessage(error), loading: false })
    }
  },

  /**
   * Slider handler.
   *
   * ADR-024: scene.envParams holds *static, location-derived defaults*, and the
   * write stays local-only — it is NOT persisted back to the API. Persisting a
   * slider drag would mutate the object every plan hangs off, which is exactly
   * the trap ADR-024 warns about.
   *
   * The values are read off here by :func:`run`, which sends them as the
   * per-run input they always were rather than as a property of the scene.
   */
  setEnvParams: (patch) =>
    set((state) => {
      if (!state.scene) return state
      return {
        scene: {
          ...state.scene,
          envParams: { ...state.scene.envParams, ...patch },
        },
      }
    }),

  /**
   * Run the simulation with the current slider values and the selected plans.
   *
   * `planIds: null` (or empty) is a baseline run. Every selected plan's
   * interventions are merged server-side into one scenario, which is what makes
   * cumulative comparison possible -- the brief's whole goal. The response's
   * overlay URLs are pushed onto `terrain` because that is what the viewer
   * reads, and both overlays are switched on: a run whose result the planner
   * cannot see is indistinguishable from a run that failed.
   */
  run: async (planIds) => {
    const { sceneId, scene } = get()
    if (!sceneId) return
    const selected = (planIds ?? []).filter(Boolean)
    set({ running: true, runError: null })
    try {
      const { windFrom, windSeason, windHeightM, windPreset, windSpeedMps } = get()
      const result = await runSimulation(sceneId, {
        rainfallMm: Number(
          scene?.envParams.precipitation ?? DEFAULT_RAINFALL_MMH,
        ) * Number(scene?.envParams.durationHours ?? DEFAULT_DURATION_HOURS),
        temperatureC: Number(
          scene?.envParams.temperature ?? DEFAULT_TEMPERATURE_C,
        ),
        tideState: (scene?.envParams.tideState ?? DEFAULT_TIDE_STATE) as
          'low' | 'mean' | 'high',
        planId: selected[0] ?? null,
        planIds: selected,
        windFrom,
        windSeason,
        windHeightM,
        windPreset,
        windSpeedMps,
      })
      set((state) => ({
        runResult: result,
        running: false,
        terrain: state.terrain
          ? {
              ...state.terrain,
              wetGridUrl: result.overlays.wetGridUrl,
              heatmapUrl: result.overlays.heatmapUrl,
            }
          : state.terrain,
        layers: { ...state.layers, wetGrid: true, heatmap: true },
      }))
    } catch (error) {
      set({ running: false, runError: errorMessage(error) })
    }
  },

  toggleLayer: (layer) =>
    set((state) => ({ layers: { ...state.layers, [layer]: !state.layers[layer] } })),

  setLayers: (layers) => set((state) => ({ layers: { ...state.layers, ...layers } })),

  /**
   * Switching mode must not move the camera. The tactical mode dims the basemap,
   * which reads as a change in what is being looked at, and a camera that jumped
   * at the same moment would make the mode look like a reload.
   */
  setViewMode: (mode) => set({ viewMode: mode }),

  /**
   * Show the corridor a board returned, and switch the wind layer on.
   *
   * Auto-enabling is the demo behaviour, not a preference: a comparison that
   * returned a corridor and drew nothing would read as a failed call. The layer
   * switch still turns it off, and an explicit `null` clears the line.
   */
  setWindCorridor: (corridor) =>
    set((state) => ({
      windCorridor: corridor,
      layers: corridor
        ? { ...state.layers, wind: true, massing25d: true }
        : state.layers,
    })),

  setWindDiagnosticUrl: (url) => set({ windDiagnosticUrl: url }),

  setWindFrom: (direction) =>
    set((state) => ({
      windFrom: direction,
      layers: { ...state.layers, wind: true, massing25d: true },
    })),

  setWindTable: (season, heightM) => set({ windSeason: season, windHeightM: heightM }),

  setWindSpeedScale: (scale) => set({ windSpeedScale: Number.isFinite(scale) && scale > 0 ? scale : 1 }),

  setWindPreset: (preset) => set({ windPreset: preset, windSpeedMps: preset === 'manual' ? get().windSpeedMps : null }),

  setWindSpeedMps: (speed) => set({
    windPreset: 'manual',
    windSpeedMps: Number.isFinite(speed) ? Math.min(45, Math.max(0.5, speed)) : 0.5,
  }),

  refreshWindHeat: async () => {
    const { sceneId, scene, windFrom, windSeason, windHeightM, windPreset, windSpeedMps } = get()
    if (!sceneId) return
    const { usePlanStore } = await import('@/state/planStore')
    const { runPlanIds, useSandboxStore } = await import('@/state/sandboxStore')
    const planIds = runPlanIds(
      usePlanStore.getState().selectedPlanIds,
      useSandboxStore.getState(),
    )
    set({ windHeatLoading: true })
    try {
      const reading = await fetchWindHeat(sceneId, {
        temperatureC: Number(scene?.envParams.temperature ?? DEFAULT_TEMPERATURE_C),
        planId: planIds[0] ?? null,
        planIds,
        windFrom,
        windSeason,
        windHeightM,
        windPreset,
        windSpeedMps,
      })
      set((state) => ({
        windHeat: reading,
        windHeatLoading: false,
        terrain: state.terrain
          ? { ...state.terrain, heatmapUrl: reading.heatmapUrl }
          : state.terrain,
        layers: { ...state.layers, heatmap: true },
      }))
    } catch {
      set({ windHeatLoading: false })
    }
  },

  clearError: () => set({ error: null }),
}))
