/**
 * Criteria fit, with the comparison.
 *
 * The closed state is four rows: the rules this sandbox is aiming at, who set
 * each one, what this screen actually reads, and one limit. Cap. 499 facts sit
 * behind Show. A blank is not sent. The read stays a broad-brush fit read.
 */
import { useEffect, useState, type ReactNode } from 'react'

import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'

import HudPanel from '@/components/HudPanel'
import { ApiError, errorMessage } from '@/api/client'
import type { ComparisonResult, ComparisonWind } from '@/api/comparisonApi'
import {
  emptyFitDraft,
  fitIsLabelled,
  postIntake,
  type FitDraft,
  type GovernmentFit,
  type IntakeResult,
  type Tri,
} from '@/api/governmentFit'
import { fetchParameterCard } from '@/api/sandboxApi'
import { useComparisonStore } from '@/state/comparisonStore'
import { useSceneStore } from '@/state/sceneStore'

const CONTROL_SX = {
  width: '100%',
  minWidth: 0,
  '& .MuiInputBase-root': { fontSize: 12, minWidth: 0 },
  '& .MuiInputBase-input': { fontSize: 12, py: 0.45, px: 1, textAlign: 'right' },
} as const

const SELECT_SX = {
  width: '100%',
  boxSizing: 'border-box',
  backgroundColor: 'rgba(5, 8, 10, 0.55)',
  color: '#dce8e2',
  colorScheme: 'dark',
  border: '1px solid',
  borderColor: 'divider',
  borderRadius: '8px',
  fontSize: 12,
  lineHeight: 1.4,
  py: 0.45,
  px: 0.75,
  fontFamily: 'inherit',
} as const

const SCHEDULE3_LABEL = {
  review: 'Review',
  not_triggered: 'No flag',
  insufficient_facts: 'Incomplete',
} as const

const SCHEDULE3_COLOUR = {
  review: '#ff9d2e',
  not_triggered: '#5cff9d',
  insufficient_facts: '#3fe0ff',
} as const

function m3(value: number): string {
  return `${Math.round(value).toLocaleString()} m³`
}

/**
 * Directions the comparison actually walked. Frontal-area ratios sit on the
 * same wind object; they are not velocity ratios, and this row does not read them.
 */
function windPaths(wind: ComparisonWind | undefined): string[] {
  if (!wind?.directions) return []
  return Object.entries(wind.directions)
    .filter(([, direction]) => {
      if (!direction) return false
      return direction.pathLengthM != null || direction.entryEdge != null || direction.blocked != null
    })
    .map(([name]) => name)
}

function greeneryHeld(result: ComparisonResult | null): string | null {
  const axis = result?.axes.find((row) => row.key === 'greenery')
  if (!axis || axis.b === null || axis.b === undefined) return null
  return `${axis.b.toFixed(2)} ha`
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Stack direction="row" spacing={1} alignItems="center" sx={{ minWidth: 0, width: '100%' }}>
      <Typography sx={{ fontSize: 12, lineHeight: 1.3, flex: '1 1 auto', minWidth: 0 }}>{label}</Typography>
      <Box sx={{ width: 128, flex: '0 0 128px', minWidth: 0, maxWidth: '46%' }}>{children}</Box>
    </Stack>
  )
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <Row label={label}>
      <TextField
        size="small"
        type="number"
        value={value}
        placeholder="—"
        onChange={(event) => onChange(event.target.value)}
        slotProps={{ htmlInput: { 'aria-label': label, step: 'any' } }}
        sx={CONTROL_SX}
      />
    </Row>
  )
}

function Choice({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: Array<{ value: string; label: string }>
  onChange: (value: string) => void
}) {
  return (
    <Row label={label}>
      <Box
        component="select"
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        sx={SELECT_SX}
      >
        {options.map((option) => (
          <option key={option.value || 'unset'} value={option.value}>
            {option.label}
          </option>
        ))}
      </Box>
    </Row>
  )
}

function TriField({
  label,
  value,
  onChange,
}: {
  label: string
  value: Tri
  onChange: (value: Tri) => void
}) {
  const options: Array<{ id: Tri; text: string }> = [
    { id: 'yes', text: 'Yes' },
    { id: 'no', text: 'No' },
  ]
  return (
    <Row label={label}>
      <Stack direction="row" spacing={0.5} justifyContent="flex-end">
        {options.map((option) => {
          const selected = value === option.id
          return (
            <Button
              key={option.id}
              size="small"
              variant={selected ? 'contained' : 'outlined'}
              aria-pressed={selected}
              onClick={() => onChange(selected ? '' : option.id)}
              sx={{ fontSize: 10, py: 0.2, minWidth: 0, px: 1 }}
            >
              {option.text}
            </Button>
          )
        })}
      </Stack>
    </Row>
  )
}

function FitLine({ label, value, colour }: { label: string; value: string; colour?: string }) {
  return (
    <Stack direction="row" spacing={1} justifyContent="space-between" alignItems="baseline" sx={{ minWidth: 0 }}>
      <Typography sx={{ fontSize: 12, lineHeight: 1.35, minWidth: 0 }}>{label}</Typography>
      <Typography
        className="hud-mono"
        sx={{ fontSize: 12, fontWeight: 600, color: colour ?? 'text.primary', textAlign: 'right', overflowWrap: 'anywhere' }}
      >
        {value}
      </Typography>
    </Stack>
  )
}

function RuleRow({
  rule,
  setBy,
  screens,
  figure,
  limit,
  children,
}: {
  rule: string
  setBy: string
  screens: string
  figure: ReactNode
  limit: string
  children?: ReactNode
}) {
  return (
    <Box sx={{ py: 0.65, borderBottom: '1px solid rgba(120, 150, 135, 0.14)', minWidth: 0 }}>
      <Typography sx={{ fontSize: 12.5, fontWeight: 600, lineHeight: 1.25 }}>{rule}</Typography>
      <Typography
        className="hud-mono"
        sx={{ fontSize: 10, lineHeight: 1.35, letterSpacing: '0.04em', textTransform: 'uppercase', color: '#3fe0ff', mt: 0.15 }}
      >
        {setBy}
      </Typography>
      <Typography sx={{ fontSize: 12, lineHeight: 1.35, mt: 0.3 }}>{screens}</Typography>
      <Box sx={{ mt: 0.25, minWidth: 0 }}>{figure}</Box>
      <Typography sx={{ fontSize: 11.5, lineHeight: 1.4, color: 'text.secondary', mt: 0.25, overflowWrap: 'anywhere' }}>
        {limit}
      </Typography>
      {children}
    </Box>
  )
}

function Figure({ held, children }: { held: boolean; children: ReactNode }) {
  return (
    <Typography
      className="hud-mono"
      sx={{ fontSize: 12, lineHeight: 1.4, color: held ? 'text.primary' : '#3fe0ff', overflowWrap: 'anywhere' }}
    >
      {children}
    </Typography>
  )
}

function section44Label(flag: string): string {
  if (flag === 'possible_specification') return 'Possible specification'
  if (flag === 'not_indicated') return 'Not indicated'
  return 'Incomplete'
}

function planningLabel(route: string | null): string {
  if (route === 'column1') return 'Column 1'
  if (route === 's16') return 'Section 16'
  if (route === 's12A') return 'Section 12A'
  return 'Column not supplied'
}

function EiaRead({ fit }: { fit: GovernmentFit }) {
  const schedule2 = fit.schedule2.length > 0 ? fit.schedule2.map((flag) => flag.item).join(', ') : 'none'
  const plan = fit.asAt.hskHtPlan
  return (
    <Box sx={{ minWidth: 0 }}>
      <FitLine
        label="Schedule 3"
        value={SCHEDULE3_LABEL[fit.schedule3.flag]}
        colour={SCHEDULE3_COLOUR[fit.schedule3.flag]}
      />
      <FitLine
        label="Schedule 2"
        value={schedule2}
        colour={fit.schedule2.length > 0 ? '#ff9d2e' : '#5cff9d'}
      />
      <FitLine label="Town planning" value={planningLabel(fit.planningPermission.route)} colour="#7d928a" />
      <FitLine
        label="Section 4(4)"
        value={section44Label(fit.section44.flag)}
        colour={fit.section44.flag === 'possible_specification' ? '#ff9d2e' : '#7d928a'}
      />
      {plan ? <FitLine label="Plan" value={plan} colour="#dce8e2" /> : null}
      <FitLine label="HKPSG noise" value="check only" colour="#3fe0ff" />
      <Typography
        className="hud-mono"
        sx={{ fontSize: 10.5, lineHeight: 1.4, color: '#ff9d2e', mt: 0.35, overflowWrap: 'anywhere' }}
      >
        {fit.screeningLabel.split('_').join('_\u200b')}
      </Typography>
    </Box>
  )
}

export default function GovernmentFitPanel() {
  const sceneId = useSceneStore((s) => s.sceneId)
  const comparison = useComparisonStore((s) => s.result)
  const [factsOpen, setFactsOpen] = useState(false)
  const [more, setMore] = useState(false)
  const [assumptionsOpen, setAssumptionsOpen] = useState(false)
  const [annexOpen, setAnnexOpen] = useState(false)
  const [unknownsOpen, setUnknownsOpen] = useState(false)
  const [draft, setDraft] = useState<FitDraft>(emptyFitDraft)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<IntakeResult | null>(null)
  const [copied, setCopied] = useState(false)
  const [soilHeld, setSoilHeld] = useState<boolean | null>(null)

  const set = <K extends keyof FitDraft>(key: K, value: FitDraft[K]) => {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  useEffect(() => {
    if (!sceneId) return
    let live = true
    void fetchParameterCard(sceneId)
      .then((card) => {
        if (!live) return
        const soil = card.entries.find((entry) => entry.key === 'soilGroup')
        setSoilHeld(soil?.value != null)
      })
      .catch(() => {
        if (live) setSoilHeld(false)
      })
    return () => {
      live = false
    }
  }, [sceneId])

  const read = async () => {
    setError(null)
    setCopied(false)
    setBusy(true)
    try {
      const next = await postIntake(draft)
      if (!fitIsLabelled(next.governmentFit)) {
        setResult(null)
        setError('The read arrived without its screening label or its unknowns list.')
        return
      }
      setUnknownsOpen(false)
      setAssumptionsOpen(false)
      setAnnexOpen(false)
      setResult(next)
    } catch (err) {
      setResult(null)
      setError(err instanceof ApiError ? errorMessage(err) : err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const copyAnnex = async () => {
    if (!result) return
    try {
      await navigator.clipboard.writeText(result.screeningBasisAnnex)
      setCopied(true)
    } catch {
      setCopied(false)
      setError('The annex is in the panel. Select it to copy.')
    }
  }

  const labelled = result !== null && fitIsLabelled(result.governmentFit)
  const fit = labelled && result ? result.governmentFit : null
  const paths = windPaths(comparison?.schemes.b.wind)
  const greenery = greeneryHeld(comparison)
  const metrics = comparison?.schemes.b.metrics
  const soilNote = soilHeld === false ? ' Soil group is not held.' : ''

  return (
    <HudPanel
      title="Criteria fit"
      sx={{ width: '100%', maxWidth: '100%', minWidth: 0, flexShrink: 0, alignSelf: 'stretch' }}
    >
      <Typography sx={{ fontSize: 12, lineHeight: 1.4, color: '#ff9d2e', fontWeight: 600, mb: 0.75 }}>
        Broad-brush fit read, not a statutory determination.
      </Typography>

      <RuleRow
        rule="Air ventilation assessment"
        setBy="Technical Circular 1/06"
        screens="Wind paths, comparing layout options"
        figure={
          <Figure held={paths.length > 0}>
            {paths.length > 0 ? `Paths compared: ${paths.join(', ')}.` : 'Wind paths are not held.'}
          </Figure>
        }
        limit="Site and local velocity ratios are not held, and frontal area and the coarse channel are not a velocity ratio."
      />

      <RuleRow
        rule="Sustainable building design"
        setBy="Buildings Department, PNAP APP-152"
        screens="Building separation, setback, site greenery"
        figure={
          <Figure held={greenery !== null}>
            {greenery !== null
              ? `Site greenery, scheme B, ${greenery}, in its own units.`
              : 'Site greenery is not held.'}
          </Figure>
        }
        limit="Separation and setback are not checked, and this row is not a concession test."
      />

      <RuleRow
        rule="Drainage impact assessment"
        setBy="Drainage Services Department"
        screens="Runoff and flood storage"
        figure={
          <Figure held={metrics != null}>
            {metrics
              ? `Runoff ${m3(metrics.runoffM3)}. Flood storage ${m3(metrics.storageCapacityM3)}. Unstored runoff ${m3(metrics.drainageDeficitM3)}, scheme B.${soilNote}`
              : `Runoff and flood storage are not held.${soilNote}`}
          </Figure>
        }
        limit="This volume is not an installed sewage capacity and not a Drainage Impact Assessment."
      />

      <RuleRow
        rule="Environmental impact assessment"
        setBy="EPD, EIA Ordinance (Cap. 499)"
        screens="Cumulative effects with neighbouring projects"
        figure={
          fit ? (
            <EiaRead fit={fit} />
          ) : (
            <Figure held={false}>No Cap. 499 facts read yet.</Figure>
          )
        }
        limit="Neighbours on the map are not a cumulative-impact finding under the Technical Memorandum."
      >
        <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between" sx={{ mt: 0.7, minWidth: 0 }}>
          <Typography sx={{ fontSize: 11.5, lineHeight: 1.35, color: 'text.secondary', minWidth: 0 }}>
            Cap. 499 facts. A blank stays blank.
          </Typography>
          <Button
            size="small"
            variant={factsOpen ? 'outlined' : 'contained'}
            aria-expanded={factsOpen}
            onClick={() => setFactsOpen((value) => !value)}
            sx={{ fontSize: 10, py: 0.25, minWidth: 0, flex: '0 0 auto' }}
          >
            {factsOpen ? 'Hide' : 'Show'}
          </Button>
        </Stack>
      </RuleRow>

      {factsOpen && (
        <Stack spacing={0.85} sx={{ mt: 1, minWidth: 0 }}>
          <NumberField label="Site area, ha" value={draft.siteAreaHa} onChange={(value) => set('siteAreaHa', value)} />
          <NumberField
            label="Share of district, %"
            value={draft.coveragePercent}
            onChange={(value) => set('coveragePercent', value)}
          />
          <NumberField
            label="District area, ha"
            value={draft.districtAreaHa}
            onChange={(value) => set('districtAreaHa', value)}
          />
          <Choice
            label="Road class"
            value={draft.roadClass}
            onChange={(value) => set('roadClass', value)}
            options={[
              { value: '', label: 'Not stated' },
              { value: 'expressway', label: 'Expressway' },
              { value: 'trunk', label: 'Trunk' },
              { value: 'primary_distributor', label: 'Primary' },
              { value: 'district_distributor', label: 'District' },
              { value: 'local_distributor', label: 'Local' },
            ]}
          />
          <Choice
            label="OZP column"
            value={draft.ozpColumn}
            onChange={(value) => set('ozpColumn', value as FitDraft['ozpColumn'])}
            options={[
              { value: '', label: 'Not stated' },
              { value: '1', label: 'Column 1' },
              { value: '2', label: 'Column 2' },
              { value: 'neither', label: 'Neither' },
            ]}
          />
          <Row label="Use">
            <TextField
              size="small"
              value={draft.use}
              placeholder="—"
              onChange={(event) => set('use', event.target.value)}
              slotProps={{ htmlInput: { 'aria-label': 'Use' } }}
              sx={CONTROL_SX}
            />
          </Row>
          <Choice
            label="Deep Bay zone"
            value={draft.deepBayBufferZone}
            onChange={(value) => set('deepBayBufferZone', value as FitDraft['deepBayBufferZone'])}
            options={[
              { value: '', label: 'Not stated' },
              { value: '1', label: 'Zone 1' },
              { value: '2', label: 'Zone 2' },
              { value: 'neither', label: 'Neither' },
            ]}
          />
          <NumberField
            label="Road receiver, m"
            value={draft.receiverDistanceRoadM}
            onChange={(value) => set('receiverDistanceRoadM', value)}
          />
          <TriField label="Road screening" value={draft.roadScreening} onChange={(value) => set('roadScreening', value)} />
          <TriField
            label="Contiguous, same persons"
            value={draft.contiguous}
            onChange={(value) => set('contiguous', value)}
          />

          <Button
            size="small"
            variant="text"
            onClick={() => setMore((value) => !value)}
            sx={{ fontSize: 11, alignSelf: 'flex-start', px: 0, color: 'text.secondary' }}
          >
            {more ? 'Hide drainage, planning, noise' : 'Drainage, planning, noise'}
          </Button>
          {more && (
            <Stack spacing={0.85}>
              <NumberField label="Road length, m" value={draft.roadLengthM} onChange={(value) => set('roadLengthM', value)} />
              <NumberField label="Population" value={draft.population} onChange={(value) => set('population', value)} />
              <NumberField label="Flats" value={draft.flatCount} onChange={(value) => set('flatCount', value)} />
              <TriField
                label="Public sewerage"
                value={draft.servedByPublicSewerage}
                onChange={(value) => set('servedByPublicSewerage', value)}
              />
              <TriField label="Exempted house" value={draft.nteh} onChange={(value) => set('nteh', value)} />
              <NumberField label="Sewage, m³/day" value={draft.stpM3PerDay} onChange={(value) => set('stpM3PerDay', value)} />
              <NumberField label="Sewage receiver, m" value={draft.stpReceiverM} onChange={(value) => set('stpReceiverM', value)} />
              <NumberField label="Channel width, m" value={draft.channelWidthM} onChange={(value) => set('channelWidthM', value)} />
              <NumberField
                label="Channel to named area, m"
                value={draft.channelNamedAreaM}
                onChange={(value) => set('channelNamedAreaM', value)}
              />
              <NumberField label="Reclamation, ha" value={draft.reclamationHa} onChange={(value) => set('reclamationHa', value)} />
              <Row label="Permission date">
                <TextField
                  size="small"
                  type="date"
                  value={draft.planningPermissionDate}
                  onChange={(event) => set('planningPermissionDate', event.target.value)}
                  slotProps={{ htmlInput: { 'aria-label': 'Planning permission date' } }}
                  sx={{
                    width: '100%',
                    '& .MuiInputBase-input': { fontSize: 12, py: 0.45, px: 1, colorScheme: 'dark' },
                  }}
                />
              </Row>
              <TriField label="Sensitive area" value={draft.inSensitiveArea} onChange={(value) => set('inSensitiveArea', value)} />
              <TriField label="Rock cavern" value={draft.rockCavern} onChange={(value) => set('rockCavern', value)} />
              <NumberField label="Portal distance, m" value={draft.rockCavernPortalM} onChange={(value) => set('rockCavernPortalM', value)} />
              <TriField label="May cause impacts" value={draft.mayCauseImpacts} onChange={(value) => set('mayCauseImpacts', value)} />
              <TriField label="Pollution-sensitive" value={draft.pollutionSensitive} onChange={(value) => set('pollutionSensitive', value)} />
              <TriField label="Major or large-scale" value={draft.majorOrLargeScale} onChange={(value) => set('majorOrLargeScale', value)} />
              <Choice
                label="Rail"
                value={draft.railType}
                onChange={(value) => set('railType', value as FitDraft['railType'])}
                options={[
                  { value: '', label: 'Not stated' },
                  { value: 'mtr', label: 'MTR' },
                  { value: 'kcr', label: 'KCR' },
                  { value: 'lrt', label: 'LRT' },
                ]}
              />
              <NumberField
                label="Rail receiver, m"
                value={draft.receiverDistanceRailM}
                onChange={(value) => set('receiverDistanceRailM', value)}
              />
              <TriField label="Inside NEF 25" value={draft.withinNef25} onChange={(value) => set('withinNef25', value)} />
            </Stack>
          )}

          <Button
            size="small"
            variant="contained"
            disabled={busy}
            onClick={() => void read()}
            sx={{ alignSelf: 'flex-start', fontSize: 11, mt: 0.25 }}
          >
            {busy ? 'Reading…' : 'Read fit'}
          </Button>

          {error && (
            <Alert severity="error" sx={{ py: 0.25 }}>
              {error}
            </Alert>
          )}
        </Stack>
      )}

      {labelled && result && (
        <Box sx={{ mt: 0.85, minWidth: 0 }}>
          <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: 'wrap' }}>
            <Button
              size="small"
              variant="outlined"
              aria-expanded={unknownsOpen}
              onClick={() => setUnknownsOpen((value) => !value)}
              sx={{ fontSize: 10 }}
            >
              {unknownsOpen ? 'Hide unknowns' : 'Unknowns'}
            </Button>
            <Button
              size="small"
              variant="outlined"
              aria-expanded={assumptionsOpen}
              onClick={() => setAssumptionsOpen((value) => !value)}
              sx={{ fontSize: 10 }}
            >
              {assumptionsOpen ? 'Hide assumptions' : 'Assumptions'}
            </Button>
            <Button size="small" variant="outlined" aria-expanded={annexOpen} onClick={() => setAnnexOpen((value) => !value)} sx={{ fontSize: 10 }}>
              {annexOpen ? 'Hide annex' : 'Annex'}
            </Button>
            <Button size="small" variant="outlined" onClick={() => void copyAnnex()} sx={{ fontSize: 10 }}>
              {copied ? 'Copied' : 'Copy annex'}
            </Button>
          </Stack>
          {unknownsOpen && (
            <Box sx={{ maxHeight: 168, overflow: 'auto', mt: 0.75, pr: 0.5, minWidth: 0 }}>
              {result.governmentFit.furtherInformation.map((line, index) => (
                <Typography
                  key={`${index}-${line.slice(0, 24)}`}
                  sx={{
                    fontSize: 11.5,
                    lineHeight: 1.45,
                    color: 'text.secondary',
                    py: 0.4,
                    borderTop: index === 0 ? 'none' : '1px solid rgba(120, 150, 135, 0.1)',
                    overflowWrap: 'anywhere',
                  }}
                >
                  {line}
                </Typography>
              ))}
            </Box>
          )}
          {assumptionsOpen && (
            <Box sx={{ mt: 0.75 }}>
              {result.governmentFit.assumptions.map((line, index) => (
                <Typography
                  key={`${index}-${line.slice(0, 24)}`}
                  sx={{ fontSize: 11.5, lineHeight: 1.45, color: 'text.secondary', py: 0.3, overflowWrap: 'anywhere' }}
                >
                  {line}
                </Typography>
              ))}
            </Box>
          )}
          {annexOpen && (
            <Box
              component="pre"
              className="hud-mono"
              sx={{
                m: 0,
                mt: 0.75,
                p: 1,
                whiteSpace: 'pre-wrap',
                overflowWrap: 'anywhere',
                fontSize: 10,
                lineHeight: 1.45,
                color: 'text.secondary',
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: '8px',
                maxHeight: 200,
                overflow: 'auto',
              }}
            >
              {result.screeningBasisAnnex}
            </Box>
          )}
        </Box>
      )}
    </HudPanel>
  )
}
