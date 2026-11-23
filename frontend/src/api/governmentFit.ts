/**
 * Broad-brush government-criteria fit at declaration intake.
 *
 * `POST /api/declarations/intake` does not store a declaration. A blank field
 * is omitted: an absent fact is not sent as zero, and the response says what
 * is still unknown. The label and `furtherInformation` travel with every read.
 */
import { http } from './client'

export const SCREENING_LABEL = 'BROAD_BRUSH_FIT_READ_NOT_A_STATUTORY_DETERMINATION'

export type Tri = '' | 'yes' | 'no'

/** What the panel holds before a read. Empty strings are not facts. */
export interface FitDraft {
  siteAreaHa: string
  coveragePercent: string
  districtAreaHa: string
  roadClass: string
  roadLengthM: string
  ozpColumn: '' | '1' | '2' | 'neither'
  use: string
  deepBayBufferZone: '' | '1' | '2' | 'neither'
  receiverDistanceRoadM: string
  roadScreening: Tri
  contiguous: Tri
  population: string
  flatCount: string
  servedByPublicSewerage: Tri
  nteh: Tri
  stpM3PerDay: string
  stpReceiverM: string
  channelWidthM: string
  channelNamedAreaM: string
  reclamationHa: string
  planningPermissionDate: string
  inSensitiveArea: Tri
  rockCavern: Tri
  rockCavernPortalM: string
  mayCauseImpacts: Tri
  pollutionSensitive: Tri
  majorOrLargeScale: Tri
  railType: '' | 'mtr' | 'kcr' | 'lrt'
  receiverDistanceRailM: string
  withinNef25: Tri
}

export function emptyFitDraft(): FitDraft {
  return {
    siteAreaHa: '',
    coveragePercent: '',
    districtAreaHa: '',
    roadClass: '',
    roadLengthM: '',
    ozpColumn: '',
    use: '',
    deepBayBufferZone: '',
    receiverDistanceRoadM: '',
    roadScreening: '',
    contiguous: '',
    population: '',
    flatCount: '',
    servedByPublicSewerage: '',
    nteh: '',
    stpM3PerDay: '',
    stpReceiverM: '',
    channelWidthM: '',
    channelNamedAreaM: '',
    reclamationHa: '',
    planningPermissionDate: '',
    inSensitiveArea: '',
    rockCavern: '',
    rockCavernPortalM: '',
    mayCauseImpacts: '',
    pollutionSensitive: '',
    majorOrLargeScale: '',
    railType: '',
    receiverDistanceRailM: '',
    withinNef25: '',
  }
}

export interface GovernmentFit {
  screeningLabel: string
  notADetermination: boolean
  schedule3: {
    triggered: boolean
    flag: 'review' | 'not_triggered' | 'insufficient_facts'
    siteAreaHa: number | null
    reason: string
  }
  schedule2: Array<{ item: string; triggered: true; reason: string }>
  planningPermission: {
    route: string | null
    isEnvironmentalPermit: false
    note: string
  }
  eaMayBeRequired: boolean | null
  assumptions: string[]
  furtherInformation: string[]
  section44: { flag: string; assertedAggregation: false; note: string }
  hkpsg: { advisoryOnly: true; passFail: false; residentialBufferM: number | null; note: string }
  asAt: Record<string, string>
}

export interface IntakeResult {
  governmentFit: GovernmentFit
  screeningBasisAnnex: string
}

/** The read is showable only with the label and a non-empty unknowns list. */
export function fitIsLabelled(fit: GovernmentFit): boolean {
  return (
    fit.notADetermination === true &&
    fit.screeningLabel === SCREENING_LABEL &&
    fit.assumptions.length > 0 &&
    fit.furtherInformation.length > 0
  )
}

function optionalNumber(raw: string, label: string): number | undefined {
  const text = raw.trim()
  if (!text) return undefined
  const value = Number(text)
  if (!Number.isFinite(value)) throw new Error(`${label} is not a number`)
  if (value < 0) throw new Error('a declared measure cannot be negative')
  return value
}

function optionalInt(raw: string, label: string): number | undefined {
  const value = optionalNumber(raw, label)
  if (value === undefined) return undefined
  if (!Number.isInteger(value)) throw new Error(`${label} is a whole number`)
  return value
}

function tri(value: Tri): boolean | undefined {
  if (value === 'yes') return true
  if (value === 'no') return false
  return undefined
}

/**
 * Facts the user actually typed. A blank is left out, so the intake cannot
 * treat "not stated" as zero, as a road class, or as a zone.
 */
export function buildIntake(draft: FitDraft): Record<string, unknown> {
  const body: Record<string, unknown> = {}
  const put = (key: string, value: unknown) => {
    if (value !== undefined && value !== '') body[key] = value
  }

  put('siteAreaHa', optionalNumber(draft.siteAreaHa, 'Site area'))
  const percent = optionalNumber(draft.coveragePercent, 'Share of district')
  if (percent !== undefined) {
    if (percent > 100) throw new Error('share of the district is from 0 to 100')
    put('coverageFraction', percent / 100)
  }
  put('districtAreaHa', optionalNumber(draft.districtAreaHa, 'District area'))
  put('roadClass', draft.roadClass)
  put('roadLengthM', optionalNumber(draft.roadLengthM, 'Road length'))
  put('ozpColumn', draft.ozpColumn)
  put('use', draft.use.trim())
  put('deepBayBufferZone', draft.deepBayBufferZone)
  put('receiverDistanceRoadM', optionalNumber(draft.receiverDistanceRoadM, 'Road receiver distance'))
  put('roadScreening', tri(draft.roadScreening))
  put('contiguousSameOrAssociatedPersons', tri(draft.contiguous))
  put('population', optionalInt(draft.population, 'Population'))
  put('flatCount', optionalInt(draft.flatCount, 'Flat count'))
  put('servedByPublicSewerage', tri(draft.servedByPublicSewerage))
  put('nteh', tri(draft.nteh))
  put('stpM3PerDay', optionalNumber(draft.stpM3PerDay, 'Sewage capacity'))
  put('stpReceiverM', optionalNumber(draft.stpReceiverM, 'Sewage receiver distance'))
  put('channelWidthM', optionalNumber(draft.channelWidthM, 'Channel width'))
  put('channelNamedAreaM', optionalNumber(draft.channelNamedAreaM, 'Channel distance'))
  put('reclamationHa', optionalNumber(draft.reclamationHa, 'Reclamation area'))
  put('planningPermissionDate', draft.planningPermissionDate)
  put('inSensitiveArea', tri(draft.inSensitiveArea))
  put('rockCavern', tri(draft.rockCavern))
  put('rockCavernPortalM', optionalNumber(draft.rockCavernPortalM, 'Portal distance'))
  put('mayCauseImpacts', tri(draft.mayCauseImpacts))
  put('pollutionSensitive', tri(draft.pollutionSensitive))
  put('majorOrLargeScale', tri(draft.majorOrLargeScale))
  put('railType', draft.railType)
  put('receiverDistanceRailM', optionalNumber(draft.receiverDistanceRailM, 'Rail receiver distance'))
  put('withinNef25', tri(draft.withinNef25))
  return body
}

export async function postIntake(draft: FitDraft): Promise<IntakeResult> {
  const { data } = await http.post<IntakeResult>('/declarations/intake', buildIntake(draft))
  return data
}
