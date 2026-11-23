/**
 * Comparison board — two schemes, separate axes, no verdict.
 *
 * The right column is narrow, so each axis is two lines rather than a table:
 * the label, then A / B / Δ. Values keep their own units and a missing value
 * stays an en dash; nothing is normalised into a score.
 *
 * B is the live selection: the toggled projects plus the sandbox's staged plan
 * (through `runPlanIds`), so confirming a natural-language intervention moves
 * the board without a second mechanism. A is a snapshot the user pins.
 *
 * Three sidecars share the same inputs: the rainfall sensitivity strip, the
 * wind corridor's toggle and the geometric shelter diagnostic. They are here,
 * not in separate panels, so a reader never has to guess which scheme a number
 * describes.
 */
import { useCallback, useEffect, useMemo, useRef } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

import HudPanel from '@/components/HudPanel'
import type { ComparisonAxis, ComparisonWind } from '@/api/comparisonApi'
import { useComparisonStore } from '@/state/comparisonStore'
import { usePlanStore } from '@/state/planStore'
import { runPlanIds, useSandboxStore } from '@/state/sandboxStore'
import { useSceneStore } from '@/state/sceneStore'

/** Short, human labels for a plan set. Empty is "today". */
function labelFor(planIds: string[], plans: ReturnType<typeof usePlanStore.getState>['plans']): string {
  if (planIds.length === 0) return 'Today (no projects)'
  const names = planIds
    .map((id) => plans.find((p) => p.planId === id)?.label)
    .filter((label): label is string => Boolean(label))
  if (names.length === 0) return `${planIds.length} scheme${planIds.length === 1 ? '' : 's'}`
  if (names.length <= 2) return names.join(' + ')
  return `${names[0]} + ${names.length - 1} more`
}

function formatValue(value: number | null, key: string, unit: string): string {
  if (value === null || value === undefined) return '—'
  if (key === 'heat') return value.toFixed(3)
  if (unit === 'm³') return Math.round(value).toLocaleString()
  if (unit === 'ha') return value.toFixed(2)
  if (unit === '%') return value.toFixed(1)
  if (unit === 'm') return value.toFixed(1)
  if (unit === 'mCD') return value.toFixed(2)
  return String(value)
}

/** Whether a signed delta is an improvement, a worsening, or neither. */
function deltaTone(axis: ComparisonAxis): 'good' | 'bad' | 'flat' {
  if (axis.delta === null || axis.delta === 0 || !axis.direction) return 'flat'
  const lowerBetter = axis.direction === 'lower-better'
  const improved = lowerBetter ? axis.delta < 0 : axis.delta > 0
  return improved ? 'good' : 'bad'
}

const TONE_COLOUR = {
  good: '#5cff9d',
  bad: '#ff9b6a',
  flat: 'rgba(190, 210, 200, 0.72)',
} as const

function WindGeometryNotes({ wind }: { wind: ComparisonWind }) {
  const ratio = wind.fadRatioByDirection?.NE
  const sidecar = wind.corridor?.properties?.sidecar
  if (!wind.corridor && !ratio && !sidecar) return null
  return (
    <>
      {ratio && (
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9, display: 'block' }}>
          NE scenario / baseline FAD{' '}
          {ratio.ratio === null ? '—' : ratio.ratio.toFixed(3)}. A comparison, not a velocity ratio.
        </Typography>
      )}
      {wind.corridor && (
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9, display: 'block' }}>
          With 2.5D massing the channel is the OpenFOAM solve for the compass
          bearing, coloured by the solved speed. The compass also picks the
          PlanD season and height. Until that file is on disk the drawing is
          the geometric corridor. Neither drawing is a velocity ratio.
        </Typography>
      )}
      {sidecar?.limitation && (
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5, display: 'block' }}>
          {sidecar.limitation}
        </Typography>
      )}
    </>
  )
}

function AxisRow({ axis }: { axis: ComparisonAxis }) {
  const tone = deltaTone(axis)
  return (
    <Box sx={{ py: 0.55, borderBottom: '1px solid rgba(120, 150, 135, 0.14)' }}>
      <Typography
        className="hud-mono"
        sx={{ fontSize: 9.5, color: 'text.secondary', lineHeight: 1.3 }}
      >
        {axis.label}
      </Typography>
      <Stack direction="row" spacing={0.5} alignItems="baseline" sx={{ mt: 0.15 }}>
        <Typography className="hud-mono" sx={{ fontSize: 11.5, width: 78 }}>
          {formatValue(axis.a, axis.key, axis.unit)}
        </Typography>
        <Typography className="hud-mono" sx={{ fontSize: 11.5, width: 78 }}>
          {formatValue(axis.b, axis.key, axis.unit)}
        </Typography>
        <Typography
          className="hud-mono"
          sx={{ fontSize: 11, flex: 1, color: TONE_COLOUR[tone] }}
        >
          {axis.comparable && axis.delta !== null
            ? `${axis.delta > 0 ? '+' : ''}${formatValue(axis.delta, axis.key, axis.unit)}`
            : axis.comparable
              ? '—'
              : 'context'}
        </Typography>
      </Stack>
    </Box>
  )
}

export default function ComparisonPanel() {
  const sceneId = useSceneStore((s) => s.sceneId)
  const scene = useSceneStore((s) => s.scene)
  const layers = useSceneStore((s) => s.layers)
  const toggleLayer = useSceneStore((s) => s.toggleLayer)
  const setLayers = useSceneStore((s) => s.setLayers)
  const plans = usePlanStore((s) => s.plans)
  const selectedPlanIds = usePlanStore((s) => s.selectedPlanIds)
  const sandbox = useSandboxStore()

  const {
    aPlanIds,
    aLabel,
    result,
    loading,
    error,
    sensitivity,
    sensitivityLoading,
    diagnostic,
    diagnosticLoading,
    setA,
    compare,
    runSensitivity,
    runDiagnostic,
    clearDiagnostic,
  } = useComparisonStore()

  const bPlanIds = useMemo(
    () => runPlanIds(selectedPlanIds, sandbox),
    // `sandbox` changes identity on refresh; the ids are what matter.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedPlanIds, sandbox.stagedPlanId, sandbox.features.length],
  )
  const bLabel = useMemo(() => labelFor(bPlanIds, plans), [bPlanIds, plans])
  // A label is a snapshot: the ids are what were compared, so the label is
  // stored beside them rather than re-derived from today's plan list.
  const effectiveALabel = aPlanIds.length === 0 ? 'Today (no projects)' : aLabel

  const rainfallMm =
    Number(scene?.envParams.precipitation ?? 50) *
    Number(scene?.envParams.durationHours ?? 1)
  const temperatureC = Number(scene?.envParams.temperature ?? 30)
  const tideState = String(scene?.envParams.tideState ?? 'low')

  const lastKey = useRef('')

  const runCompare = useCallback(async () => {
    if (!sceneId) return
    lastKey.current = `${bPlanIds.join(',')}|${rainfallMm}|${tideState}`
    await compare(
      sceneId,
      { planIds: bPlanIds, label: bLabel },
      { rainfallMm, temperatureC, tideState },
    )
  }, [sceneId, compare, bPlanIds, bLabel, rainfallMm, temperatureC, tideState])

  // The board follows the schemes. Once a comparison exists, toggling a project
  // — or confirming an intervention onto the sandbox — re-reads it after a short
  // pause, so a sentence in the chat makes the board move. A first comparison is
  // still an explicit press: nothing fetches on mount.
  useEffect(() => {
    if (!result) return
    const key = `${bPlanIds.join(',')}|${rainfallMm}|${tideState}`
    if (key === lastKey.current) return
    const timer = setTimeout(() => {
      void runCompare()
    }, 500)
    return () => clearTimeout(timer)
    // `result` is read only as a "has this run before" gate.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bPlanIds.join(','), rainfallMm, tideState])

  const onPinA = () => {
    setA(bPlanIds, bLabel)
    lastKey.current = ''
  }

  return (
    <HudPanel
      title="Compare"
      right={
        loading ? (
          <CircularProgress size={10} sx={{ color: '#5cff9d' }} />
        ) : result ? (
          <Typography className="hud-mono" sx={{ fontSize: 9, color: '#5cff9d' }}>
            no combined score
          </Typography>
        ) : undefined
      }
      sx={{ width: '100%' }}
    >
      <Stack spacing={0.75}>
        <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1.5, p: 0.9 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Box sx={{ minWidth: 0 }}>
              <Typography className="hud-label" sx={{ fontSize: 8.5 }}>
                A
              </Typography>
              <Typography className="hud-mono" noWrap sx={{ fontSize: 10 }}>
                {aPlanIds.length === 0 ? 'Today (no projects)' : effectiveALabel}
              </Typography>
            </Box>
            <Button size="small" onClick={onPinA} sx={{ fontSize: 9, minWidth: 0, px: 0.75 }}>
              Use current
            </Button>
          </Stack>
          <Box sx={{ mt: 0.6 }}>
            <Typography className="hud-label" sx={{ fontSize: 8.5 }}>
              B — live selection
            </Typography>
            <Typography className="hud-mono" noWrap sx={{ fontSize: 10 }}>
              {bLabel}
            </Typography>
          </Box>
        </Box>

        <Button
          fullWidth
          size="small"
          variant={result ? 'outlined' : 'contained'}
          onClick={() => void runCompare()}
          disabled={!sceneId || loading || (aPlanIds.join(',') === bPlanIds.join(',') && Boolean(result))}
          sx={{ fontSize: 10, py: 0.45 }}
        >
          {aPlanIds.join(',') === bPlanIds.join(',') && result ? 'A and B are the same' : 'Compare A vs B'}
        </Button>

        {error && (
          <Typography variant="caption" sx={{ color: '#ff9b6a' }}>
            {error}
          </Typography>
        )}

        {result && (
          <>
            <Stack direction="row" spacing={0.5} sx={{ mt: 0.3 }}>
              <Typography className="hud-label" sx={{ fontSize: 8.5, width: 78 }}>
                A
              </Typography>
              <Typography className="hud-label" sx={{ fontSize: 8.5, width: 78 }}>
                B
              </Typography>
              <Typography className="hud-label" sx={{ fontSize: 8.5 }}>
                B − A
              </Typography>
            </Stack>
            {result.axes.map((axis) => (
              <AxisRow key={axis.key} axis={axis} />
            ))}

            <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9 }}>
              {result.inputs.rainfallMm.toFixed(0)} mm storm · tide{' '}
              {result.inputs.tide.tailwaterM.toFixed(2)} mCD · {result.status}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9 }}>
              {result.whyNoCombinedScore}
            </Typography>

            {/* ---- the wind sidecar ------------------------------------- */}
            <Box sx={{ pt: 0.75, borderTop: '1px solid', borderColor: 'divider' }}>
              <Stack direction="row" spacing={0.75} alignItems="center">
                <Typography className="hud-label" sx={{ fontSize: 8.5, flex: 1 }}>
                  Wind corridor — geometry, not a velocity ratio
                </Typography>
                <Button
                  size="small"
                  variant={layers.wind ? 'contained' : 'outlined'}
                  onClick={() => {
                    const next = !layers.wind
                    toggleLayer('wind')
                    if (next) setLayers({ massing25d: true })
                  }}
                  disabled={!result.schemes.b.wind.corridor}
                  sx={{ fontSize: 9, minWidth: 0, px: 0.75, py: 0.15 }}
                >
                  {layers.wind ? 'On' : 'Off'}
                </Button>
              </Stack>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9 }}>
                First obstruction from NE:{' '}
                {formatValue(result.schemes.b.wind.firstObstructionMeanM, 'wind', 'm')}
                {' m'} (A{' '}
                {formatValue(result.schemes.a.wind.firstObstructionMeanM, 'wind', 'm')} m).
                Under the published prevailing inflow (NE/ENE/E).
              </Typography>
              <WindGeometryNotes wind={result.schemes.b.wind} />
              {result.windChannel && (
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9, display: 'block' }}>
                  Window inflow {result.windChannel.inflow.headlineDirection ?? '—'}
                  {result.windChannel.inflow.headlineFrequency != null
                    ? ` (${(result.windChannel.inflow.headlineFrequency * 100).toFixed(1)}%)`
                    : ''}
                  {' · '}
                  {result.windChannel.options
                    .filter((option) => option.bFirstObstructionMeanM != null)
                    .map((option) => `${option.direction} ${option.bFirstObstructionMeanM!.toFixed(1)} m`)
                    .join(' · ')}
                  . SVR and LVR are not computed.
                </Typography>
              )}
              {result.dataCollection && (
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9, display: 'block' }}>
                  Data collection: {result.dataCollection.inventory.map((row) => (
                    row.count == null ? row.name : `${row.name} (${row.count})`
                  )).join(', ')}
                  . Committed projects are not held. Not a cumulative assessment.
                </Typography>
              )}
              <Stack direction="row" spacing={0.75} sx={{ mt: 0.5 }}>
                <Button
                  size="small"
                  variant="outlined"
                  disabled={diagnosticLoading || !sceneId}
                  onClick={() => sceneId && void runDiagnostic(sceneId, bPlanIds)}
                  sx={{ fontSize: 9, py: 0.2 }}
                >
                  {diagnosticLoading ? 'Reading…' : 'Shelter index'}
                </Button>
                {diagnostic && (
                  <Button
                    size="small"
                    onClick={clearDiagnostic}
                    sx={{ fontSize: 9, py: 0.2 }}
                  >
                    Hide
                  </Button>
                )}
              </Stack>
              {diagnostic && (
                <>
                  <Typography className="hud-mono" sx={{ fontSize: 10, mt: 0.4 }}>
                    Mean shelter {diagnostic.meanShelterIndex.toFixed(3)} · max{' '}
                    {diagnostic.maxShelterIndex.toFixed(3)} ({diagnostic.direction})
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5 }}>
                    {diagnostic.warning}
                  </Typography>
                </>
              )}
            </Box>

            {/* ---- one sensitivity knob --------------------------------- */}
            <Box sx={{ pt: 0.75, borderTop: '1px solid', borderColor: 'divider' }}>
              <Button
                size="small"
                variant="outlined"
                disabled={sensitivityLoading || !sceneId}
                onClick={() => sceneId && void runSensitivity(sceneId, bPlanIds, rainfallMm)}
                sx={{ fontSize: 9, py: 0.2 }}
              >
                {sensitivityLoading ? 'Re-running…' : 'Rainfall ±20%'}
              </Button>
              {sensitivity && (
                <>
                  <Stack direction="row" spacing={0.5} sx={{ mt: 0.5 }}>
                    {sensitivity.rows.map((row) => (
                      <Box key={row.label} sx={{ flex: 1 }}>
                        <Typography className="hud-label" sx={{ fontSize: 8 }}>
                          {row.label}
                        </Typography>
                        <Typography className="hud-mono" sx={{ fontSize: 10 }}>
                          {Math.round(row.unstoredM3).toLocaleString()}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5 }}>
                    m³ unstored. {sensitivity.driver}
                  </Typography>
                </>
              )}
            </Box>
          </>
        )}

        {!result && !loading && (
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9 }}>
            B is the live selection, including interventions confirmed onto the
            sandbox. Compare it with today, or pin a scheme as A and compare two.
          </Typography>
        )}
      </Stack>
    </HudPanel>
  )
}
