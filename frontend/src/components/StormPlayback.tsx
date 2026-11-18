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
 *
 * ## Why it looks like this
 *
 * The panel is one card in the right-hand HUD column, so it follows that column's
 * idiom rather than inventing controls: uppercase mono micro-labels, tabular
 * readouts, a hairline inner box for numbers, and the caveat as an amber rule.
 * The timeline strip and the depth legend are the two things a playhead needs
 * that the other cards do not: where you are in the storm, and what a colour on
 * the map means. Without the legend the overlay is decoration.
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

/**
 * The retained-depth ramp, in the same order and at the same stops as
 * `_DEPTH_COLOURS` / `_DEPTH_STOPS_M` in `services/storm_playback.py`. Keep them
 * in step: the legend is the only thing that makes a frame's colour mean a depth.
 */
const DEPTH_LEGEND: Array<{ depth: string; colour: string }> = [
  { depth: '0', colour: 'rgb(70, 150, 220)' },
  { depth: '2', colour: 'rgb(46, 160, 230)' },
  { depth: '5', colour: 'rgb(30, 190, 225)' },
  { depth: '10', colour: 'rgb(40, 220, 190)' },
  { depth: '20', colour: 'rgb(120, 240, 140)' },
  { depth: '40', colour: 'rgb(210, 255, 120)' },
]

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
  const peakIndex = playback
    ? playback.hyetograph.mmPerHour.indexOf(Math.max(...playback.hyetograph.mmPerHour))
    : -1
  const peakRain = playback ? Math.max(...playback.hyetograph.mmPerHour, 0) : 0
  const cumulativeMm = playback
    ? playback.hours.slice(0, frame + 1).reduce((sum, h) => sum + h.rainfallMm, 0)
    : 0

  return (
    <HudPanel
      title="Storm playback"
      right={
        loading ? (
          <CircularProgress size={10} sx={{ color: '#5cff9d' }} />
        ) : playback ? (
          <Typography className="hud-mono" sx={{ fontSize: 9, color: '#5cff9d' }}>
            SCREENING
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
        <Stack spacing={0.75}>
          {/* The same hairline box the Compare card uses for its inputs: what
              the playhead will run on, before there is anything to read. */}
          <Box
            sx={{
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1.5,
              px: 0.9,
              py: 0.7,
            }}
          >
            <Typography className="hud-label" sx={{ fontSize: 8.5 }}>
              Storm
            </Typography>
            <Typography className="hud-mono" noWrap sx={{ fontSize: 10 }}>
              2023-09-07 · HKO HQ
            </Typography>
            <Typography className="hud-label" sx={{ fontSize: 8.5, mt: 0.6 }}>
              Runs on
            </Typography>
            <Typography className="hud-mono" noWrap sx={{ fontSize: 10 }}>
              live selection · {planIds.length} plan{planIds.length === 1 ? '' : 's'}
            </Typography>
          </Box>
          <Button
            fullWidth
            size="small"
            variant="contained"
            onClick={() => void load()}
            disabled={!sceneId || loading}
            sx={{ fontSize: 10, py: 0.45 }}
          >
            {loading ? 'Running the storm…' : 'Load the storm'}
          </Button>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5 }}>
            The hourly march the ledger already runs, drawn hour by hour. No second
            simulation: the frames and the totals come from one march.
          </Typography>
        </Stack>
      )}

      {playback && hour && (
        <Stack spacing={0.75}>
          <Stack direction="row" spacing={0.5} alignItems="center">
            <Button
              size="small"
              variant="contained"
              onClick={() => setPlaying((p) => !p)}
              sx={{ fontSize: 9, py: 0.2, minWidth: 52 }}
            >
              {playing ? 'Pause' : 'Play'}
            </Button>
            <Button
              size="small"
              variant="outlined"
              aria-label="Previous hour"
              onClick={() => {
                setPlaying(false)
                setFrame((f) => Math.max(0, f - 1))
              }}
              disabled={frame === 0}
              sx={{ fontSize: 9, py: 0.2, minWidth: 26, px: 0.5 }}
            >
              ‹
            </Button>
            <Button
              size="small"
              variant="outlined"
              aria-label="Next hour"
              onClick={() => {
                setPlaying(false)
                setFrame((f) => Math.min(playback.hours.length - 1, f + 1))
              }}
              disabled={frame >= playback.hours.length - 1}
              sx={{ fontSize: 9, py: 0.2, minWidth: 26, px: 0.5 }}
            >
              ›
            </Button>
            <Typography
              className="hud-mono"
              sx={{ fontSize: 10, ml: 'auto', color: '#5cff9d' }}
            >
              h{hour.hour}/{playback.hours.length - 1}
            </Typography>
            <Button size="small" onClick={close} sx={{ fontSize: 9, minWidth: 0, px: 0.5 }}>
              Close
            </Button>
          </Stack>

          {/* Timeline: every hour of the hyetograph at once, bar height = that
              hour's intensity, the playhead picked out in signal green. Reads as
              "where is this frame in the storm" without moving the slider. */}
          <Box sx={{ display: 'flex', gap: '2px', alignItems: 'flex-end', height: 30 }}>
            {playback.hours.map((h, i) => {
              const active = i === frame
              const share = peakRain > 0 ? h.rainfallMm / peakRain : 0
              return (
                <Box
                  key={h.hour}
                  component="button"
                  type="button"
                  aria-label={`Hour ${h.hour}, ${h.rainfallMm.toFixed(0)} mm/h`}
                  aria-current={active ? 'true' : undefined}
                  onClick={() => {
                    setPlaying(false)
                    setFrame(i)
                  }}
                  sx={{
                    flex: 1,
                    height: '100%',
                    p: 0,
                    border: '1px solid',
                    borderColor: active ? 'rgba(92,255,157,0.6)' : 'divider',
                    borderRadius: 0.75,
                    background: 'rgba(5, 8, 10, 0.5)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'flex-end',
                    overflow: 'hidden',
                    '&:hover': { borderColor: 'rgba(92,255,157,0.35)' },
                  }}
                >
                  <Box
                    sx={{
                      width: '100%',
                      // px, not %: an hour at 6 mm/h is 4% of the peak and a
                      // percentage floor (6%) hid it under the 30 px cell.
                      height: `${Math.max(3, share * 27)}px`,
                      backgroundColor: active ? '#5cff9d' : 'rgba(63, 224, 255, 0.45)',
                    }}
                  />
                </Box>
              )
            })}
          </Box>

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
            sx={{ py: 0.25 }}
          />

          <Stack direction="row" spacing={0.75} alignItems="baseline">
            <Typography className="hud-mono" sx={{ fontSize: 13, lineHeight: 1.2 }}>
              {hour.rainfallMm.toFixed(0)} mm/h
            </Typography>
            <Typography className="hud-mono" sx={{ fontSize: 9, color: 'text.secondary' }}>
              {cumulativeMm.toFixed(0)} mm so far
            </Typography>
            {peakIndex >= 0 && (
              <Typography
                className="hud-label"
                sx={{ fontSize: 8, ml: 'auto', color: frame === peakIndex ? '#5cff9d' : undefined }}
              >
                peak h{peakIndex}
              </Typography>
            )}
          </Stack>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 0.75,
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1.5,
              px: 0.9,
              py: 0.7,
            }}
          >
            <Metric label="Standing" value={`${Math.round(hour.standingM3).toLocaleString()} m³`} />
            <Metric label="Retained" value={`${Math.round(hour.storedM3).toLocaleString()} m³`} />
            <Metric label="Drained" value={`${Math.round(hour.drainedM3).toLocaleString()} m³`} />
            <Metric
              label="Wet cells"
              value={`${hour.wetCells.toLocaleString()} · ${(hour.meanPoolDepthM * 100).toFixed(1)} cm`}
            />
          </Box>

          {/* The legend is not decoration: without it a colour on the map is
              just a colour. Stops match the backend ramp, in centimetres. */}
          <Box>
            <Stack direction="row" spacing="2px">
              {DEPTH_LEGEND.map((stop) => (
                <Box
                  key={stop.depth}
                  sx={{ flex: 1, height: 5, borderRadius: 0.5, backgroundColor: stop.colour }}
                />
              ))}
            </Stack>
            <Stack direction="row" spacing="2px" sx={{ mt: 0.3 }}>
              {DEPTH_LEGEND.map((stop) => (
                <Typography
                  key={stop.depth}
                  className="hud-mono"
                  sx={{ flex: 1, fontSize: 7.5, color: 'text.secondary', textAlign: 'center' }}
                >
                  {stop.depth}
                </Typography>
              ))}
            </Stack>
            <Typography className="hud-label" sx={{ fontSize: 8, mt: 0.3 }}>
              Retained depth · cm · fixed scale across hours
            </Typography>
          </Box>

          <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5 }}>
            {playback.hyetograph.label}. {playback.frameNote}
          </Typography>
          <Box
            sx={{
              borderLeft: '2px solid rgba(255, 157, 46, 0.55)',
              pl: 0.75,
              py: 0.1,
            }}
          >
            <Typography sx={{ fontSize: 8.5, color: '#ffcf8f', lineHeight: 1.45 }}>
              {playback.warning}
            </Typography>
          </Box>
        </Stack>
      )}
    </HudPanel>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography className="hud-label" sx={{ fontSize: 8 }}>
        {label}
      </Typography>
      <Typography className="hud-mono" noWrap sx={{ fontSize: 10 }}>
        {value}
      </Typography>
    </Box>
  )
}
