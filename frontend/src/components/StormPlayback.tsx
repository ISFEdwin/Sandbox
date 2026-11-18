/**
 * Playhead for one named storm.
 *
 * Each frame is that hour's precipitation-flow picture from
 * `GET /drainage/hourly`. The screening line stays on the bar, and the
 * storm name is in the label. Play is what moves the wet grid.
 */
import { useEffect, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Slider from '@mui/material/Slider'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

import { fetchHourlyStorm, type HourlyStorm } from '@/api/demoApi'
import { errorMessage } from '@/api/client'
import { useSceneStore } from '@/state/sceneStore'

const STORM = 'hko_2023_09_07'
// Cesium classifies a draped hour a few seconds after the PNG decodes.
// A shorter gap replaces the image before that finishes, and the map
// stays on the aerial photo while the label moves.
const FRAME_MS = 4500

export default function StormPlayback() {
  const sceneId = useSceneStore((s) => s.sceneId)
  const showStormFrame = useSceneStore((s) => s.showStormFrame)
  const [storm, setStorm] = useState<HourlyStorm | null>(null)
  const [hour, setHour] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [engaged, setEngaged] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sceneId) return
    let cancel = false
    setError(null)
    fetchHourlyStorm(sceneId, STORM)
      .then((data) => {
        if (cancel) return
        setStorm(data)
        setHour(0)
      })
      .catch((err: unknown) => {
        if (!cancel) setError(errorMessage(err))
      })
    return () => {
      cancel = true
    }
  }, [sceneId])

  useEffect(() => {
    if (!playing || !storm || storm.hours < 1) return
    const id = window.setInterval(() => {
      setHour((current) => (current + 1) % storm.hours)
    }, FRAME_MS)
    return () => window.clearInterval(id)
  }, [playing, storm])

  useEffect(() => {
    if (!engaged || !storm) return
    const frame = storm.frames.find((item) => item.hour === hour)
    if (frame) showStormFrame(frame.url)
  }, [engaged, storm, hour, showStormFrame])

  const frame = storm?.frames.find((item) => item.hour === hour)
  const balanced = storm?.massBalance.enforced && storm.massBalance.residualM3 === 0

  return (
    <Box
      sx={{
        position: 'absolute',
        bottom: 78,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1200,
        width: 'min(420px, calc(100vw - 720px))',
        px: 1.25,
        py: 1,
        borderRadius: '10px',
        border: '1px solid',
        borderColor: 'divider',
        backgroundColor: 'rgba(8, 13, 12, 0.9)',
        backdropFilter: 'blur(16px)',
        pointerEvents: 'auto',
      }}
    >
      <Stack direction="row" spacing={1} alignItems="center">
        <Button
          size="small"
          variant={playing ? 'contained' : 'outlined'}
          disabled={!storm}
          aria-label={playing ? 'Pause the storm' : 'Play the storm'}
          onClick={() => {
            setEngaged(true)
            setPlaying((on) => !on)
          }}
          sx={{ minWidth: 64, textTransform: 'none', fontSize: 11 }}
        >
          {playing ? 'Pause' : 'Play'}
        </Button>
        <Box sx={{ flex: 1, px: 0.5 }}>
          <Slider
            size="small"
            aria-label="Storm hour"
            min={0}
            max={Math.max((storm?.hours ?? 1) - 1, 0)}
            step={1}
            value={hour}
            disabled={!storm}
            onChange={(_event, next) => {
              setEngaged(true)
              setPlaying(false)
              setHour(Array.isArray(next) ? next[0] : next)
            }}
          />
        </Box>
      </Stack>
      <Typography className="hud-mono" sx={{ fontSize: 11, lineHeight: 1.35 }}>
        {storm
          ? `${storm.hyetograph.name} · hour ${hour + 1} of ${storm.hours}`
            + ` · ${frame?.rainfallMm ?? '—'} mm`
            + (frame?.standingM3 != null ? ` · standing ${Math.round(frame.standingM3).toLocaleString('en-US')} m³` : '')
          : STORM}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: 9, lineHeight: 1.35 }}>
        {storm?.screeningLine ?? 'Not a flood prediction. Drainage rate is the DSD design standard. No pipe network.'}
        {balanced ? ' Mass balance holds.' : ''}
      </Typography>
      {error && (
        <Typography variant="caption" color="error" sx={{ display: 'block', fontSize: 9 }}>
          {error}
        </Typography>
      )}
    </Box>
  )
}
