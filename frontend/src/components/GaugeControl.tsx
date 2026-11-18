/**
 * One input that is not a slider.
 *
 * Live reads HKO (Wetland Park rainfall, Tsim Bei Tsui predicted tide).
 * Recorded is the cited 2023-09-07 peak, so the same run can be repeated
 * when the live hour is dry. Either way the numbers are written into the
 * rainfall and tide the Run button already sends.
 */
import { useState } from 'react'
import Button from '@mui/material/Button'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

import { fetchGauge, type GaugeReading } from '@/api/demoApi'
import { errorMessage } from '@/api/client'
import type { TideState } from '@/api/types'
import { peekTypedRainfall, rememberTypedRainfall, takeTypedRainfall } from '@/state/gaugeBaseline'
import { useSceneStore } from '@/state/sceneStore'

type Source = 'typed' | 'live' | 'recorded'

export default function GaugeControl() {
  const scene = useSceneStore((s) => s.scene)
  const setEnvParams = useSceneStore((s) => s.setEnvParams)
  const provenance = useSceneStore((s) => s.inputProvenance)
  const setInputProvenance = useSceneStore((s) => s.setInputProvenance)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const active: Source = provenance?.mode ?? 'typed'
  const intensity = Number(scene?.envParams.precipitation ?? 50)
  const durationH = Number(scene?.envParams.durationHours ?? 1)
  const tideState = (scene?.envParams.tideState ?? 'low') as TideState

  const rememberTyped = () => {
    if (provenance) return
    rememberTypedRainfall({ precipitation: intensity, durationHours: durationH, tideState })
  }

  const apply = (reading: GaugeReading) => {
    const previous = peekTypedRainfall()
    setEnvParams({
      precipitation: reading.rainfallMm,
      durationHours: 1,
      tideState: reading.tideState ?? previous?.tideState ?? tideState,
    })
    setInputProvenance({
      kind: 'gauge',
      mode: reading.mode,
      label: reading.label,
      observedAt: reading.observedAt,
    })
    setNote(reading.fallback ?? reading.note)
    setError(null)
  }

  const load = async (mode: 'live' | 'recorded') => {
    if (!scene?.sceneId) return
    rememberTyped()
    setBusy(true)
    setError(null)
    try {
      apply(await fetchGauge(scene.sceneId, mode))
    } catch (err: unknown) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const useTyped = () => {
    const previous = takeTypedRainfall()
    if (previous) {
      setEnvParams({
        precipitation: previous.precipitation,
        durationHours: previous.durationHours,
        tideState: previous.tideState,
      })
    }
    setInputProvenance(null)
    setNote(null)
    setError(null)
  }

  return (
    <Stack spacing={0.5}>
      <Typography className="hud-label" sx={{ fontSize: 8.5 }}>
        Rainfall source
      </Typography>
      <Stack direction="row" spacing={0.5}>
        {([
          ['typed', 'Typed', useTyped],
          ['live', 'Live gauge', () => void load('live')],
          ['recorded', 'Recorded', () => void load('recorded')],
        ] as const).map(([id, label, onClick]) => (
          <Button
            key={id}
            size="small"
            variant={active === id ? 'contained' : 'outlined'}
            disabled={busy || !scene}
            onClick={onClick}
            sx={{ flex: 1, minWidth: 0, px: 0.5, py: 0.25, fontSize: 10, lineHeight: 1.3, textTransform: 'none' }}
          >
            {label}
          </Button>
        ))}
      </Stack>
      {provenance && (
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5, lineHeight: 1.3 }}>
          {provenance.label}
        </Typography>
      )}
      {note && (
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5, lineHeight: 1.3 }}>
          {note}
        </Typography>
      )}
      {error && (
        <Typography variant="caption" color="error" sx={{ fontSize: 8.5 }}>
          {error}
        </Typography>
      )}
    </Stack>
  )
}
