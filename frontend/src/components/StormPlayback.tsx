/**
 * Storm playhead: the hourly march, frame by frame.
 *
 * The backend runs the existing `hourly_storm_simulation` and writes one PNG per
 * hour (`services/storm_playback.py`); this panel swaps the wet-grid overlay's
 * URL to that frame. No new physics, and the panel keeps the simulation's own
 * warning on screen for the whole playback.
 *
 * What a frame shows is the per-cell **retained/pool** depth — the state the
 * march actually carries forward. Standing water is a district scalar in that
 * model, so it is shown as a number beside the frame rather than painted where
 * the model does not put it.
 *
 * The run's own overlay is restored when the playback is closed, unless a newer
 * run has replaced it in the meantime.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Slider from '@mui/material/Slider'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

import HudPanel from '@/components/HudPanel'
import { fetchStormPlayback, type StormPlayback as Playback } from '@/api/comparisonApi'
import { errorMessage } from '@/api/client'
import { runPlanIds, useSandboxStore } from '@/state/sandboxStore'
import { usePlanStore } from '@/state/planStore'
import { useSceneStore } from '@/state/sceneStore'

const HYETOGRAPH = 'hko_2023_09_07'
const FRAME_MS = 950

/** Are we currently showing one of the playback's frames? */
function showingPlaybackFrame(playback: Playback | null): boolean {
  const url = useSceneStore.getState().terrain?.wetGridUrl ?? ''
  return Boolean(playback?.hours.some((h) => h.overlayUrl && h.overlayUrl === url))
}

function showFrame(playback: Playback, index: number): void {
  const frame = playback.hours[index]
  if (!frame?.overlayUrl) return
  useSceneStore.setState((state) => ({
    terrain: state.terrain
      ? { ...state.terrain, wetGridUrl: frame.overlayUrl }
      : state.terrain,
    layers: { ...state.layers, wetGrid: true },
  }))
}

export default function StormPlayback() {
  const sceneId = useSceneStore((s) => s.sceneId)
  const selectedPlanIds = usePlanStore((s) => s.selectedPlanIds)
  const sandbox = useSandboxStore()

  const [playback, setPlayback] = useState<Playback | null>(null)
  const [frame, setFrame] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const originalUrl = useRef<string | null | undefined>(undefined)

  const planIds = runPlanIds(selectedPlanIds, sandbox)

  const load = useCallback(async () => {
    if (!sceneId) return
    setLoading(true)
    setError(null)
    try {
      originalUrl.current = useSceneStore.getState().terrain?.wetGridUrl ?? null
      const data = await fetchStormPlayback(sceneId, {
        hyetographName: HYETOGRAPH,
        planIds,
      })
      setPlayback(data)
      setFrame(0)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [sceneId, planIds])

  const close = useCallback(() => {
    setPlaying(false)
    const current = useSceneStore.getState().terrain?.wetGridUrl ?? null
    const original = originalUrl.current
    // Restore only if the overlay is still one of ours: a live run that landed
    // mid-playback owns the layer now, and putting an old frame back would make
    // the stats panel and the map describe different runs.
    if (original !== undefined && showingPlaybackFrame(playback) && current !== original) {
      useSceneStore.setState((state) => ({
        terrain: state.terrain
          ? { ...state.terrain, wetGridUrl: original }
          : state.terrain,
      }))
    }
    originalUrl.current = undefined
    setPlayback(null)
    setFrame(0)
  }, [playback])

  // Advancing the playhead. The frame index is the only state this timer
  // touches: pushing the overlay URL from inside a `setFrame` updater updated
  // another component (the viewer's store) during render, which React warns
  // about and can drop -- the map then kept the first frame while the readout
  // advanced. The effect below moves the map, once, from committed state.
  useEffect(() => {
    if (!playing || !playback) return
    if (frame >= playback.hours.length - 1) {
      setPlaying(false)
      return
    }
    const timer = setTimeout(() => setFrame((current) => current + 1), FRAME_MS)
    return () => clearTimeout(timer)
  }, [playing, playback, frame])

  // The map follows the playhead, and the slider gets the same path.
  useEffect(() => {
    if (!playback) return
    showFrame(playback, frame)
  }, [playback, frame])

  // Leaving the panel restores the run overlay, same rule as `close`.
  useEffect(
    () => () => {
      const current = useSceneStore.getState().terrain?.wetGridUrl ?? ''
      const original = originalUrl.current
      if (original !== undefined && current.includes('/rasters/storm/') && current !== original) {
        useSceneStore.setState((state) => ({
          terrain: state.terrain
            ? { ...state.terrain, wetGridUrl: original }
            : state.terrain,
        }))
      }
    },
    [],
  )

  const hour = playback?.hours[frame]
  const peakHour = playback?.hyetograph.mmPerHour.indexOf(
    Math.max(...(playback?.hyetograph.mmPerHour ?? [0])),
  )

  return (
    <HudPanel
      title="Storm playback"
      right={
        loading ? (
          <CircularProgress size={10} sx={{ color: '#5cff9d' }} />
        ) : playback ? (
          <Typography className="hud-mono" sx={{ fontSize: 9, color: '#5cff9d' }}>
            {playback.hyetograph.name}
          </Typography>
        ) : undefined
      }
      sx={{ width: '100%' }}
    >
      {error && (
        <Typography variant="caption" sx={{ color: '#ff9b6a' }}>
          {error}
        </Typography>
      )}

      {!playback && (
        <>
          <Button
            size="small"
            variant="outlined"
            onClick={() => void load()}
            disabled={!sceneId || loading}
            sx={{ fontSize: 9, py: 0.2 }}
          >
            {loading ? 'Running the storm…' : 'Load 2023-09-07 storm'}
          </Button>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5, display: 'block', mt: 0.5 }}>
            The hourly march the ledger already runs, drawn hour by hour. Runs on
            the live selection.
          </Typography>
        </>
      )}

      {playback && hour && (
        <>
          <Stack direction="row" spacing={0.75} alignItems="center">
            <Button
              size="small"
              variant="contained"
              onClick={() => setPlaying((p) => !p)}
              sx={{ fontSize: 9, py: 0.2, minWidth: 52 }}
            >
              {playing ? 'Pause' : 'Play'}
            </Button>
            <Button size="small" onClick={close} sx={{ fontSize: 9, py: 0.2 }}>
              Close
            </Button>
            <Typography className="hud-mono" sx={{ fontSize: 10, ml: 'auto' }}>
              h{hour.hour} · {hour.rainfallMm.toFixed(0)} mm/h
            </Typography>
          </Stack>

          <Slider
            size="small"
            min={0}
            max={playback.hours.length - 1}
            step={1}
            value={frame}
            onChange={(_, value) => {
              const next = Array.isArray(value) ? value[0] : value
              setPlaying(false)
              setFrame(next)
            }}
            sx={{ mt: 0.5, py: 0.5 }}
          />

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 0.5,
              fontFamily: 'monospace',
            }}
          >
            <Metric label="Standing" value={`${Math.round(hour.standingM3).toLocaleString()} m³`} />
            <Metric label="Retained" value={`${Math.round(hour.storedM3).toLocaleString()} m³`} />
            <Metric label="Drained" value={`${Math.round(hour.drainedM3).toLocaleString()} m³`} />
            <Metric label="Wet cells" value={String(hour.wetCells)} />
          </Box>

          <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5, display: 'block', mt: 0.4 }}>
            {playback.hyetograph.label}
            {peakHour !== undefined && peakHour >= 0 ? ` · peak h${peakHour}` : ''}.{' '}
            {playback.frameNote}
          </Typography>
          <Typography variant="caption" sx={{ fontSize: 8.5, color: '#ffcf8f', display: 'block', mt: 0.3 }}>
            {playback.warning}
          </Typography>
        </>
      )}
    </HudPanel>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography className="hud-label" sx={{ fontSize: 8 }}>
        {label}
      </Typography>
      <Typography className="hud-mono" sx={{ fontSize: 10 }}>
        {value}
      </Typography>
    </Box>
  )
}
