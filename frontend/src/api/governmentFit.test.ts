/**
 * The intake body is only what was typed. A blank must not become zero, and a
 * share of the district is a percent converted to a fraction, not 50 ha.
 */
import { describe, expect, it } from 'vitest'

import { buildIntake, emptyFitDraft, fitIsLabelled, SCREENING_LABEL, type GovernmentFit } from './governmentFit'

function labelled(over: Partial<GovernmentFit> = {}): GovernmentFit {
  return {
    screeningLabel: SCREENING_LABEL,
    notADetermination: true,
    schedule3: { triggered: false, flag: 'insufficient_facts', siteAreaHa: null, reason: '' },
    schedule2: [],
    planningPermission: { route: null, isEnvironmentalPermit: false, note: '' },
    eaMayBeRequired: null,
    assumptions: ['broad-brush'],
    furtherInformation: ['zone Notes were not read'],
    section44: { flag: 'not_indicated', assertedAggregation: false, note: '' },
    hkpsg: { advisoryOnly: true, passFail: false, residentialBufferM: null, note: '' },
    asAt: {},
    ...over,
  }
}

describe('buildIntake', () => {
  it('sends nothing when every field is blank', () => {
    expect(buildIntake(emptyFitDraft())).toEqual({})
  })

  it('sends hectares and a road class, and leaves a blank length out', () => {
    const draft = emptyFitDraft()
    draft.siteAreaHa = '60'
    draft.roadClass = 'trunk'
    expect(buildIntake(draft)).toEqual({ siteAreaHa: 60, roadClass: 'trunk' })
  })

  it('converts a share of the district to a fraction and does not invent site area', () => {
    const draft = emptyFitDraft()
    draft.coveragePercent = '30'
    draft.districtAreaHa = '43.5'
    expect(buildIntake(draft)).toEqual({ coverageFraction: 0.3, districtAreaHa: 43.5 })
  })

  it('sends a share with no district area, so the read cannot treat the share as 50 ha', () => {
    const draft = emptyFitDraft()
    draft.coveragePercent = '30'
    expect(buildIntake(draft)).toEqual({ coverageFraction: 0.3 })
  })

  it('sends a local distributor when that class is chosen', () => {
    const draft = emptyFitDraft()
    draft.roadClass = 'local_distributor'
    expect(buildIntake(draft)).toEqual({ roadClass: 'local_distributor' })
  })

  it('sends a tri-state only when it is answered', () => {
    const draft = emptyFitDraft()
    draft.roadScreening = 'no'
    draft.contiguous = 'yes'
    expect(buildIntake(draft)).toEqual({ roadScreening: false, contiguousSameOrAssociatedPersons: true })
  })

  it('refuses a negative measure before the request', () => {
    const draft = emptyFitDraft()
    draft.siteAreaHa = '-1'
    expect(() => buildIntake(draft)).toThrow(/cannot be negative/)
  })
})

describe('fitIsLabelled', () => {
  it('accepts a read that keeps the label and the unknowns list', () => {
    expect(fitIsLabelled(labelled())).toBe(true)
  })

  it('rejects a read that drops the label or the unknowns list', () => {
    expect(fitIsLabelled(labelled({ screeningLabel: '' }))).toBe(false)
    expect(fitIsLabelled(labelled({ notADetermination: false }))).toBe(false)
    expect(fitIsLabelled(labelled({ furtherInformation: [] }))).toBe(false)
    expect(fitIsLabelled(labelled({ assumptions: [] }))).toBe(false)
  })
})
