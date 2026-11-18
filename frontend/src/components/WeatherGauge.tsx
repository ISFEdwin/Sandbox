/**
 * The gauge: where the storm number came from.
 *
 * Two honest sources, never conflated:
 *
 * - **recorded** — the project's cited Hong Kong storm series, deterministic and
 *   offline. Its peak hour is the published HKO HQ reading; its hourly shape is
 *   a reconstruction, and the panel says so.
 * - **live** — one attempt at HKO's public current report. What that payload
 *   carries is rainfall *since midnight*, not an hourly intensity, so the
 *   "Use" button is disabled and the reading is shown in its own units. The
 *   backend refuses to convert it because the interval is not in the payload;
 *   this panel refuses to hide that refusal.
 *
 * Using a reading writes the same env params the Run button already sends. No
 * second run path, and no number that the stats panel cannot cite.
 */
import { useCallback, useEffect, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

import HudPanel from '@/components/HudPanel'
import { fetchWeather, type WeatherReading } from '@/api/comparisonApi'
import { errorMessage } from '@/api/client'
import { useSceneStore } from '@/state/sceneStore'

export default function WeatherGauge() {
  const sceneId = useSceneStore((s) => s.sceneId)
  const setEnvParams = useSceneStore((s) => s.setEnvParams)
  const envParams = useSceneStore((s) => s.scene?.envParams)

  const [mode, setMode] = useState<'recorded' | 'live'>('recorded')
  const [reading, setReading] = useState<WeatherReading | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(
    async (next: 'recorded' | 'live') => {
      if (!sceneId) return
      setLoading(true)
      setError(null)
      try {
        setReading(await fetchWeather(sceneId, next))
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setLoading(false)
      }
    },
    [sceneId],
  )

  useEffect(() => {
    void load('recorded')
  }, [load])

  const onMode = (next: 'recorded' | 'live') => {
    setMode(next)
    void load(next)
  }

  const useReading = () => {
    if (!reading?.usableAsIntensity || reading.rainfallMmHr === null) return
    // A one-hour storm at the reading's peak. Duration is explicit so the stats
    // panel's total (intensity × duration) is not a hidden default.
    setEnvParams({ precipitation: reading.rainfallMmHr, durationHours: 1 })
  }

  const applied = Number(envParams?.precipitation ?? 0) * Number(envParams?.durationHours ?? 0)

  return (
    <HudPanel
      title="Rain gauge"
      right={
        loading ? (
          <CircularProgress size={10} sx={{ color: '#5cff9d' }} />
        ) : (
          <Typography className="hud-mono" sx={{ fontSize: 9, color: 'text.secondary' }}>
            {mode === 'live' ? 'LIVE' : 'RECORDED'}
          </Typography>
        )
      }
      sx={{ width: '100%' }}
    >
      <Stack direction="row" spacing={0.75} sx={{ mb: 0.75 }}>
        <Button
          size="small"
          variant={mode === 'recorded' ? 'contained' : 'outlined'}
          onClick={() => onMode('recorded')}
          sx={{ fontSize: 9, py: 0.2 }}
        >
          Recorded
        </Button>
        <Button
          size="small"
          variant={mode === 'live' ? 'contained' : 'outlined'}
          onClick={() => onMode('live')}
          sx={{ fontSize: 9, py: 0.2 }}
        >
          HKO live
        </Button>
      </Stack>

      {error && (
        <Typography variant="caption" sx={{ color: '#ff9b6a' }}>
          {error}
        </Typography>
      )}

      {reading && (
        <Box>
          <Typography className="hud-mono" sx={{ fontSize: 15, lineHeight: 1.2 }}>
            {reading.rainfallMmHr !== null
              ? `${reading.rainfallMmHr.toFixed(1)} mm/h`
              : reading.sinceMidnightMm !== null
                ? `${reading.sinceMidnightMm.toFixed(1)} mm`
                : '—'}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9, display: 'block' }}>
            {reading.label}
            {reading.station ? ` · ${reading.station}` : ''}
            {reading.observedAt ? ` · ${reading.observedAt}` : ''}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9, display: 'block', mt: 0.4 }}>
            {reading.note}
          </Typography>
          {reading.fallbackReason && (
            <Typography variant="caption" sx={{ fontSize: 8.5, color: '#ffb98f', display: 'block', mt: 0.3 }}>
              Feed: {reading.fallbackReason}
            </Typography>
          )}

          <Stack direction="row" spacing={0.75} alignItems="center" sx={{ mt: 0.6 }}>
            <Button
              size="small"
              variant="outlined"
              onClick={useReading}
              disabled={!reading.usableAsIntensity}
              sx={{ fontSize: 9, py: 0.2 }}
            >
              Use for next run
            </Button>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5 }}>
              now: {applied.toFixed(0)} mm
            </Typography>
          </Stack>
          {!reading.usableAsIntensity && (
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5, display: 'block', mt: 0.3 }}>
              Shown in its own units. Not converted into a storm intensity.
            </Typography>
          )}
        </Box>
      )}
    </HudPanel>
  )
}
