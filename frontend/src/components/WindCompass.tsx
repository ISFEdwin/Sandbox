/**
 * Bearing and PlanD table for the OpenFOAM channel.
 *
 * The rose picks the direction the wind blows from. The chips pick which
 * verified site-wind table supplies the inlet speed. Paths come from the
 * annual 500 m solve for that bearing. Another table scales those speeds by
 * the ratio of the two derived inlets.
 */
import { useEffect, useState } from 'react'
import Box from '@mui/material/Box'
import Slider from '@mui/material/Slider'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import Typography from '@mui/material/Typography'

import { usePlanStore } from '@/state/planStore'
import { useSandboxStore } from '@/state/sandboxStore'
import { useSceneStore } from '@/state/sceneStore'

const SIGNAL_MPS = {
  signal3: 41 / 3.6,
  signal8: 63 / 3.6,
  signal10: 118 / 3.6,
} as const

const ORDER = [
  'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW',
] as const

const DEGREES: Record<string, number> = {
  N: 0, NNE: 22.5, NE: 45, ENE: 67.5, E: 90, ESE: 112.5,
  SE: 135, SSE: 157.5, S: 180, SSW: 202.5, SW: 225, WSW: 247.5,
  W: 270, WNW: 292.5, NW: 315, NNW: 337.5,
}

const CARDINAL = new Set(['N', 'E', 'S', 'W'])
const INTER = new Set(['NE', 'SE', 'SW', 'NW'])

interface WindCell {
  frequency: number | null
  derivedMeanSpeedMps: number | null
  inletSpeedMps: number | null
}

interface WindIndex {
  scaleNote?: string
  tables: Record<string, Record<string, { fileUrl?: string; directions: Record<string, WindCell> }>>
}

function windShift(deltaC: number): string {
  if (Math.abs(deltaC) < 0.05) return 'about the same'
  return `${Math.abs(deltaC).toFixed(1)} °C ${deltaC < 0 ? 'cooler' : 'warmer'}`
}

function polar(deg: number, radius: number, cx: number, cy: number) {
  const rad = (deg * Math.PI) / 180
  return { x: cx + radius * Math.sin(rad), y: cy - radius * Math.cos(rad) }
}

export default function WindCompass({ offsetLeft }: { offsetLeft: number }) {
  const windOn = useSceneStore((s) => s.layers.wind)
  const windFrom = useSceneStore((s) => s.windFrom)
  const season = useSceneStore((s) => s.windSeason)
  const heightM = useSceneStore((s) => s.windHeightM)
  const setWindFrom = useSceneStore((s) => s.setWindFrom)
  const setWindTable = useSceneStore((s) => s.setWindTable)
  const setWindSpeedScale = useSceneStore((s) => s.setWindSpeedScale)
  const preset = useSceneStore((s) => s.windPreset)
  const manualSpeed = useSceneStore((s) => s.windSpeedMps)
  const setWindPreset = useSceneStore((s) => s.setWindPreset)
  const setWindSpeedMps = useSceneStore((s) => s.setWindSpeedMps)
  const refreshWindHeat = useSceneStore((s) => s.refreshWindHeat)
  const sceneId = useSceneStore((s) => s.sceneId)
  const heatLoading = useSceneStore((s) => s.windHeatLoading)
  const windHeat = useSceneStore((s) => s.windHeat)
  const temperature = useSceneStore((s) => s.scene?.envParams.temperature)
  const planKey = usePlanStore((s) => s.selectedPlanIds.join(','))
  const stagedPlanId = useSandboxStore((s) => s.stagedPlanId)
  const placedCount = useSandboxStore((s) => s.features.length)
  const [index, setIndex] = useState<WindIndex | null>(null)
  const [missing, setMissing] = useState(false)

  useEffect(() => {
    let cancelled = false
    void fetch('/static/openfoam/wind_index.json')
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error('missing'))))
      .then((body: WindIndex) => {
        if (!cancelled) setIndex(body)
      })
      .catch(() => {
        if (!cancelled) setMissing(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const table = index?.tables?.[season]?.[String(heightM)]
  const solved = index?.tables?.annual?.['500']?.directions?.[windFrom]
  const selected = table?.directions?.[windFrom]

  const presetSpeed = preset === 'manual'
    ? manualSpeed
    : preset === 'pland'
      ? selected?.inletSpeedMps ?? null
      : SIGNAL_MPS[preset]
  const shownSpeed = presetSpeed ?? selected?.inletSpeedMps ?? null

  useEffect(() => {
    const reference = solved?.inletSpeedMps
    if (shownSpeed && reference) setWindSpeedScale(shownSpeed / reference)
  }, [shownSpeed, solved?.inletSpeedMps, setWindSpeedScale])

  useEffect(() => {
    if (!windOn || !sceneId) return
    const timer = window.setTimeout(() => {
      void refreshWindHeat()
    }, 450)
    return () => window.clearTimeout(timer)
  }, [windOn, sceneId, windFrom, season, heightM, preset, manualSpeed, temperature, planKey, stagedPlanId, placedCount, refreshWindHeat])

  if (!windOn) return null

  const cx = 150
  const cy = 150
  const bearing = DEGREES[windFrom] ?? 0
  const tail = polar(bearing, 108, cx, cy)
  const head = polar(bearing, 46, cx, cy)
  const left = polar(bearing - 8, 62, cx, cy)
  const right = polar(bearing + 8, 62, cx, cy)

  return (
    <Box
      sx={{
        position: 'absolute',
        bottom: 16,
        left: offsetLeft,
        zIndex: 1250,
        width: 332,
        transform: 'scale(0.86)',
        transformOrigin: 'bottom left',
        p: 1.25,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: '12px',
        backgroundColor: 'rgba(8, 13, 12, 0.82)',
        backdropFilter: 'blur(12px)',
        pointerEvents: 'auto',
        transition: 'left 0.2s',
      }}
    >
      <Typography className="hud-label" sx={{ fontSize: 9, mb: 0.5 }}>
        Wind from
      </Typography>
      <Box sx={{ position: 'relative', width: 300, height: 300, mx: 'auto' }}>
        <svg width="300" height="300" viewBox="0 0 300 300" aria-hidden>
          <circle cx={cx} cy={cy} r={112} fill="none" stroke="rgba(255,246,232,0.28)" strokeWidth={1.5} />
          <circle cx={cx} cy={cy} r={4} fill="#fff6e8" />
          <line x1={tail.x} y1={tail.y} x2={head.x} y2={head.y} stroke="#ffb020" strokeWidth={3} />
          <polygon points={`${head.x},${head.y} ${left.x},${left.y} ${right.x},${right.y}`} fill="#ffb020" />
          {ORDER.map((name) => {
            const deg = DEGREES[name]
            const inner = polar(deg, 96, cx, cy)
            const outer = polar(deg, 108, cx, cy)
            const label = polar(deg, CARDINAL.has(name) ? 132 : 126, cx, cy)
            const on = name === windFrom
            return (
              <g key={name}>
                <line
                  x1={inner.x}
                  y1={inner.y}
                  x2={outer.x}
                  y2={outer.y}
                  stroke={on ? '#ffb020' : 'rgba(255,246,232,0.45)'}
                  strokeWidth={CARDINAL.has(name) ? 2 : 1}
                />
                {(CARDINAL.has(name) || INTER.has(name)) && (
                  <text
                    x={label.x}
                    y={label.y}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill={on ? '#ffb020' : '#fff6e8'}
                    fontSize={CARDINAL.has(name) ? 18 : 11}
                    fontFamily="Inter, system-ui, sans-serif"
                  >
                    {name}
                  </text>
                )}
              </g>
            )
          })}
          <text x={cx} y={cy + 22} textAnchor="middle" fill="#fff6e8" fontSize={13} fontFamily="Inter, system-ui, sans-serif">
            {windFrom}
          </text>
        </svg>
        {ORDER.map((name) => {
          const spot = polar(DEGREES[name], 96, 150, 150)
          const size = CARDINAL.has(name) ? 28 : 18
          return (
            <Box
              key={name}
              component="button"
              type="button"
              aria-label={`Wind from ${name}`}
              aria-pressed={name === windFrom}
              onClick={() => setWindFrom(name)}
              sx={{
                position: 'absolute',
                left: spot.x - size / 2,
                top: spot.y - size / 2,
                width: size,
                height: size,
                p: 0,
                border: 'none',
                borderRadius: '50%',
                background: name === windFrom ? 'rgba(255,176,32,0.35)' : 'transparent',
                cursor: 'pointer',
              }}
            />
          )
        })}
      </Box>

      <ToggleButtonGroup
        exclusive
        size="small"
        fullWidth
        value={season}
        onChange={(_, next: 'annual' | 'summer' | 'winter' | null) => {
          if (next) setWindTable(next, heightM)
        }}
        aria-label="Site wind season"
        sx={{ mt: 0.5, '& .MuiToggleButton-root': { fontSize: 10, py: 0.3, textTransform: 'none' } }}
      >
        <ToggleButton value="annual">Annual</ToggleButton>
        <ToggleButton value="summer">Summer</ToggleButton>
        <ToggleButton value="winter">Winter</ToggleButton>
      </ToggleButtonGroup>
      <ToggleButtonGroup
        exclusive
        size="small"
        fullWidth
        value={heightM}
        onChange={(_, next: 500 | 300 | 200 | null) => {
          if (next) setWindTable(season, next)
        }}
        aria-label="Site wind height"
        sx={{ mt: 0.5, '& .MuiToggleButton-root': { fontSize: 10, py: 0.3, textTransform: 'none' } }}
      >
        <ToggleButton value={500}>500 m</ToggleButton>
        <ToggleButton value={300}>300 m</ToggleButton>
        <ToggleButton value={200}>200 m</ToggleButton>
      </ToggleButtonGroup>

      <Typography className="hud-mono" sx={{ fontSize: 11, mt: 0.75 }}>
        {shownSpeed == null
          ? 'No derived speed in this table'
          : `${shownSpeed.toFixed(2)} m/s at 10 m`}
      </Typography>
      <Slider
        size="small"
        min={0.5}
        max={40}
        step={0.1}
        value={shownSpeed ?? 2}
        aria-label="Wind speed at 10 m"
        onChange={(_, value) => {
          if (typeof value === 'number') setWindSpeedMps(value)
        }}
        sx={{ mt: 0.5, color: '#ffb020', py: 0.5 }}
      />
      <ToggleButtonGroup
        exclusive
        size="small"
        fullWidth
        value={preset === 'manual' ? null : preset}
        onChange={(_, next: 'pland' | 'signal3' | 'signal8' | 'signal10' | null) => {
          if (next) setWindPreset(next)
        }}
        aria-label="Wind speed preset"
        sx={{ mt: 0.25, '& .MuiToggleButton-root': { fontSize: 9, py: 0.25, px: 0.4, textTransform: 'none' } }}
      >
        <ToggleButton value="pland">PlanD</ToggleButton>
        <ToggleButton value="signal3">Signal 3</ToggleButton>
        <ToggleButton value="signal8">Signal 8</ToggleButton>
        <ToggleButton value="signal10">Signal 10</ToggleButton>
      </ToggleButtonGroup>
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5, display: 'block', mt: 0.35 }}>
        {preset === 'signal3' && 'HKO Signal 3 onset, sustained 41 km/h. '}
        {preset === 'signal8' && 'HKO Signal 8 onset, sustained 63 km/h. '}
        {preset === 'signal10' && 'HKO Signal 10 onset, sustained 118 km/h. '}
        {preset === 'manual' && 'Manual 10 m speed. '}
        Colour follows the solved fast and slow threads. A faster preset pushes that band hotter. Display traces fill the channel. Not a new solve.
        {heatLoading ? ' Reading the heat field…' : ''}
      </Typography>
      {windHeat?.ventilation?.applied && (
        <Typography className="hud-mono" sx={{ fontSize: 10, display: 'block', mt: 0.25 }}>
          Surface {windHeat.surfaceMeanC.toFixed(1)} °C
          {' · open '}
          {windShift(-windHeat.ventilation.openCellCoolingC)}
          {' · sheltered '}
          {windShift(-windHeat.ventilation.shelteredCellCoolingC)}
        </Typography>
      )}
      <Box sx={{ display: 'flex', gap: 0.4, mt: 0.35 }}>
        {['#7ec8ff', '#ffe7a8', '#ffb020', '#e23b2f'].map((colour) => (
          <Box key={colour} sx={{ flex: 1, height: 4, bgcolor: colour }} />
        ))}
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8, display: 'flex', justifyContent: 'space-between' }}>
        <span>slower</span>
        <span>faster</span>
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9, display: 'block' }}>
        {selected?.frequency == null
          ? 'Occurrence not in the selected table.'
          : `Occurrence ${(selected.frequency * 100).toFixed(1)}%. Derived ${selected.derivedMeanSpeedMps?.toFixed(2) ?? '—'} m/s at ${heightM} m.`}
      </Typography>
      {table?.fileUrl && (
        <Typography variant="caption" sx={{ fontSize: 9, display: 'block' }}>
          <a href={table.fileUrl} target="_blank" rel="noreferrer" style={{ color: '#ffe7a8' }}>
            PlanD table
          </a>
        </Typography>
      )}
      {!(season === 'annual' && heightM === 500) && index?.scaleNote && (
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5, display: 'block', mt: 0.25 }}>
          {index.scaleNote}
        </Typography>
      )}
      {missing && (
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: 8.5, display: 'block' }}>
          The PlanD index is not on disk, so the speeds stay on the solved file.
        </Typography>
      )}
    </Box>
  )
}
