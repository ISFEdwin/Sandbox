/**
 * Rainfall at ±20%, from `storage_ledger`.
 *
 * Three volumes and one sentence. The sentence's deltas are the engine's
 * low and high minus its baseline. No score, no pass or fail.
 */
import { useEffect, useState } from 'react'
import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

import { fetchSensitivity, type SensitivityReport } from '@/api/demoApi'
import { errorMessage } from '@/api/client'
import HudPanel from '@/components/HudPanel'
import { DEFAULT_DURATION_HOURS, DEFAULT_RAINFALL_MMH, useSceneStore } from '@/state/sceneStore'

function m3(value: number): string {
  return Math.round(value).toLocaleString('en-US')
}

export default function SensitivityStrip() {
  const sceneId = useSceneStore((s) => s.sceneId)
  const scene = useSceneStore((s) => s.scene)
  const rainfallMm = Number(scene?.envParams.precipitation ?? DEFAULT_RAINFALL_MMH)
    * Number(scene?.envParams.durationHours ?? DEFAULT_DURATION_HOURS)
  const [report, setReport] = useState<SensitivityReport | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sceneId || !Number.isFinite(rainfallMm)) return
    let cancel = false
    setError(null)
    fetchSensitivity(sceneId, rainfallMm)
      .then((data) => {
        if (!cancel) setReport(data)
      })
      .catch((err: unknown) => {
        if (!cancel) setError(errorMessage(err))
      })
    return () => {
      cancel = true
    }
  }, [sceneId, rainfallMm])

  const point = (name: SensitivityReport['points'][number]['name']) =>
    report?.points.find((item) => item.name === name)

  return (
    <HudPanel title="Sensitivity" right={
      <Typography className="hud-mono" sx={{ fontSize: 9, color: 'text.secondary' }}>
        rainfall ±20%
      </Typography>
    }>
      {!report && !error && (
        <Typography variant="caption" color="text.secondary">
          Computing the ledger at {rainfallMm.toFixed(0)} mm ±20%…
        </Typography>
      )}
      {error && (
        <Typography variant="caption" color="error">{error}</Typography>
      )}
      {report && (
        <Stack spacing={0.75}>
          <Stack direction="row" spacing={1} justifyContent="space-between">
            {(['low', 'baseline', 'high'] as const).map((name) => {
              const item = point(name)
              return (
                <Box key={name} sx={{ flex: 1 }}>
                  <Typography className="hud-label" sx={{ fontSize: 8.5 }}>
                    {name}{item ? ` · ${item.rainfallMm.toFixed(0)} mm` : ''}
                  </Typography>
                  <Typography className="hud-mono" sx={{ fontSize: 13, fontWeight: 600 }}>
                    {item ? `${m3(item.unstoredM3)} m³` : '—'}
                  </Typography>
                </Box>
              )
            })}
          </Stack>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9, lineHeight: 1.35 }}>
            {report.sentence}
          </Typography>
        </Stack>
      )}
    </HudPanel>
  )
}
