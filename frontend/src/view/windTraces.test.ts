import { describe, expect, it } from 'vitest'

import { densifyTraces, speedColour, speedsAlong, type TraceFeature } from './windTraces'

function line(lat: number, speed: number): TraceFeature {
  const coordinates = [0, 1, 2, 3, 4].map((step) => [113.99 + step * 0.0001, lat, 12])
  return {
    type: 'Feature',
    properties: { speedMps: speed, speedMinMps: speed - 0.2, speedMaxMps: speed + 0.4 },
    geometry: { type: 'LineString', coordinates },
  }
}

describe('densifyTraces', () => {
  it('inserts traces between close parallel paths and leaves a wide gap empty', () => {
    // About 22 m apart in latitude, then a jump of roughly 200 m.
    const close = [line(22.43100, 2.2), line(22.43120, 3.1)]
    const far = line(22.43300, 1.1)
    const out = densifyTraces([...close, far], 90)
    const inserted = out.filter((feature) => feature.properties?.displayTrace)
    expect(inserted).toHaveLength(2)
    expect(inserted[0].properties?.speedMps).toBeGreaterThan(2.2)
    expect(inserted[0].properties?.speedMps).toBeLessThan(3.1)
  })

  it('spans a line with its recorded speed range', () => {
    expect(speedsAlong(1, 3)).toEqual([1, 2.3, 3, 1.7])
  })

  it('keeps a fast thread hotter than a slow one, and a signal hotter than the solved inlet', () => {
    // Past the cream stop the red channel sits at the top of the ramp, so the
    // hotter thread is the one with less green and blue left.
    const cool = (css: string) => {
      const match = css.match(/rgb\((\d+), (\d+), (\d+)/)
      return Number(match?.[2]) + Number(match?.[3])
    }
    expect(cool(speedColour(4.2, 1))).toBeLessThan(cool(speedColour(2.1, 1)))
    expect(cool(speedColour(3, 6))).toBeLessThan(cool(speedColour(3, 1)))
    expect(cool(speedColour(2.1, 6))).toBeGreaterThan(cool(speedColour(4.2, 6)))
  })
})