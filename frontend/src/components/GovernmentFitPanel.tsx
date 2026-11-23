/**
 * Criteria fit, beside the parameter card.
 *
 * A short fact list, then a flag summary. Blank fields are not sent. The
 * result stays a broad-brush fit read: the screening label and the unknowns
 * list travel with it.
 */
import { useEffect, useRef, useState, type ReactNode } from 'react'

import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'

import HudPanel from '@/components/HudPanel'
import { ApiError, errorMessage } from '@/api/client'
import {
  emptyFitDraft,
  fitIsLabelled,
  postIntake,
  type FitDraft,
  type GovernmentFit,
  type IntakeResult,
  type Tri,
} from '@/api/governmentFit'

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

function headline(fit: GovernmentFit): string {
  const schedule2 = fit.schedule2.length > 0 ? fit.schedule2.map((flag) => flag.item).join(' ') : 'no Sch 2'
  return `Sch 3 ${SCHEDULE3_LABEL[fit.schedule3.flag].toLowerCase()} · ${schedule2}`
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

function FlagRow({
  label,
  value,
  colour,
  detail,
}: {
  label: string
  value: string
  colour: string
  detail?: string
}) {
  return (
    <Box sx={{ py: 0.65, borderBottom: '1px solid rgba(120, 150, 135, 0.14)', minWidth: 0 }}>
      <Stack direction="row" spacing={1} justifyContent="space-between" alignItems="baseline" sx={{ minWidth: 0 }}>
        <Typography sx={{ fontSize: 12, flex: '1 1 auto', minWidth: 0 }}>{label}</Typography>
        <Typography className="hud-mono" sx={{ fontSize: 12, fontWeight: 600, color: colour, flex: '0 0 auto' }}>
          {value}
        </Typography>
      </Stack>
      {detail && (
        <Typography sx={{ fontSize: 11.5, lineHeight: 1.45, color: 'text.secondary', mt: 0.25, overflowWrap: 'anywhere' }}>
          {detail}
        </Typography>
      )}
    </Box>
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

function FitReadout({ fit }: { fit: GovernmentFit }) {
  const schedule2 = fit.schedule2.length > 0 ? fit.schedule2.map((flag) => flag.item).join(', ') : 'None'
  const plan = fit.asAt.hskHtPlan
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography sx={{ fontSize: 12.5, lineHeight: 1.4, color: '#ff9d2e', fontWeight: 600 }}>
        Not a determination
      </Typography>
      <Typography sx={{ fontSize: 11.5, lineHeight: 1.45, color: 'text.secondary', overflowWrap: 'anywhere' }}>
        A fit read of the facts below. It is not an environmental permit and not a section 16 decision.
        {plan ? ` Plan ${plan}.` : ''}
      </Typography>

      <Box sx={{ mt: 0.75 }}>
        <FlagRow
          label="Schedule 3"
          value={SCHEDULE3_LABEL[fit.schedule3.flag]}
          colour={SCHEDULE3_COLOUR[fit.schedule3.flag]}
          detail={fit.schedule3.reason}
        />
        <FlagRow
          label="Schedule 2"
          value={schedule2}
          colour={fit.schedule2.length > 0 ? '#ff9d2e' : '#5cff9d'}
          detail={
            fit.schedule2.length > 0
              ? fit.schedule2.map((flag) => flag.reason).join(' ')
              : 'No Schedule 2 item was flagged from the facts that were typed.'
          }
        />
        <FlagRow
          label="Town planning"
          value={planningLabel(fit.planningPermission.route)}
          colour="text.secondary"
          detail={fit.planningPermission.note}
        />
        <FlagRow
          label="Environmental assessment"
          value={fit.eaMayBeRequired === true ? 'May be required' : fit.eaMayBeRequired === false ? 'Not indicated' : 'Not stated'}
          colour={fit.eaMayBeRequired ? '#ff9d2e' : '#7d928a'}
        />
        <FlagRow
          label="Section 4(4)"
          value={section44Label(fit.section44.flag)}
          colour={fit.section44.flag === 'possible_specification' ? '#ff9d2e' : '#7d928a'}
          detail={fit.section44.note}
        />
        <FlagRow
          label="HKPSG noise"
          value="Check only"
          colour="#3fe0ff"
          detail={fit.hkpsg.note}
        />
      </Box>

      <Typography className="hud-label" sx={{ mt: 1.25, mb: 0.5 }}>
        Still unknown · {fit.furtherInformation.length}
      </Typography>
      <Box sx={{ maxHeight: 168, overflow: 'auto', pr: 0.5, minWidth: 0 }}>
        {fit.furtherInformation.map((line, index) => (
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
    </Box>
  )
}

export default function GovernmentFitPanel() {
  const [open, setOpen] = useState(false)
  const [more, setMore] = useState(false)
  const [assumptionsOpen, setAssumptionsOpen] = useState(false)
  const [annexOpen, setAnnexOpen] = useState(false)
  const [draft, setDraft] = useState<FitDraft>(emptyFitDraft)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<IntakeResult | null>(null)
  const [copied, setCopied] = useState(false)
  const resultRef = useRef<HTMLDivElement>(null)

  const set = <K extends keyof FitDraft>(key: K, value: FitDraft[K]) => {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  useEffect(() => {
    if (!result) return
    resultRef.current?.scrollIntoView({ block: 'nearest' })
  }, [result])

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

  return (
    <HudPanel
      title="Criteria fit"
      right={
        labelled ? (
          <Typography className="hud-mono" sx={{ fontSize: 9, color: '#ff9d2e', textAlign: 'right' }}>
            {headline(result.governmentFit)}
          </Typography>
        ) : undefined
      }
      sx={{ width: '100%', maxWidth: '100%', minWidth: 0, overflow: 'hidden' }}
    >
      <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
        <Typography sx={{ fontSize: 12, color: 'text.secondary', lineHeight: 1.4, minWidth: 0 }}>
          Gates these facts appear to touch. A blank stays blank.
        </Typography>
        <Button
          size="small"
          variant={open ? 'outlined' : 'contained'}
          onClick={() => setOpen((value) => !value)}
          sx={{ fontSize: 10, py: 0.25, minWidth: 0, flex: '0 0 auto' }}
        >
          {open ? 'Hide' : 'Show'}
        </Button>
      </Stack>

      {open && (
        <Stack spacing={0.85} sx={{ mt: 1.25, minWidth: 0 }}>
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

          {labelled && result && (
            <Box
              ref={resultRef}
              sx={{ border: '1px solid', borderColor: 'divider', borderRadius: '8px', p: 1, minWidth: 0 }}
            >
              <FitReadout fit={result.governmentFit} />
              <Stack direction="row" spacing={0.5} sx={{ mt: 1, flexWrap: 'wrap' }}>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={() => setAssumptionsOpen((value) => !value)}
                  sx={{ fontSize: 10 }}
                >
                  {assumptionsOpen ? 'Hide assumptions' : 'Assumptions'}
                </Button>
                <Button size="small" variant="outlined" onClick={() => setAnnexOpen((value) => !value)} sx={{ fontSize: 10 }}>
                  {annexOpen ? 'Hide annex' : 'Annex'}
                </Button>
                <Button size="small" variant="outlined" onClick={() => void copyAnnex()} sx={{ fontSize: 10 }}>
                  {copied ? 'Copied' : 'Copy annex'}
                </Button>
              </Stack>
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
        </Stack>
      )}
    </HudPanel>
  )
}
