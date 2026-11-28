/**
 * Display traces between solved OpenFOAM streamlines.
 *
 * The channel plants seeds across the inlet at five heights, every other cell
 * on a diagonal and every cell on a cardinal, so the drawn field is still
 * sparser than a wind-tunnel picture. Filling the gap between two solved paths
 * that stay close produces more threads in the channel and leaves a gap where
 * the paths split around a building. An inserted thread is a display trace: its
 * speed is the blend of the two solved speeds. It is not an additional solve.
 */

export interface TraceFeature {
  type: 'Feature'
  properties?: {
    speedMps?: number
    speedMinMps?: number
    speedMaxMps?: number
    displayTrace?: boolean
  }
  geometry?: { type: string; coordinates?: number[][] }
}

const M_PER_DEG_LAT = 111_320

function metres(a: number[], b: number[]): number {
  const lat = ((a[1] + b[1]) / 2) * (Math.PI / 180)
  const dx = (a[0] - b[0]) * M_PER_DEG_LAT * Math.cos(lat)
  const dy = (a[1] - b[1]) * M_PER_DEG_LAT
  return Math.hypot(dx, dy)
}

/** Position across the inflow, so neighbouring seeds sort beside each other. */
function crossKey(coord: number[], bearingDeg: number): number {
  const rad = (bearingDeg * Math.PI) / 180
  return coord[0] * Math.cos(rad) - coord[1] * Math.sin(rad)
}

function sample(coords: number[][], index: number, count: number): number[] {
  const at = Math.round((index * (coords.length - 1)) / Math.max(count - 1, 1))
  return coords[Math.min(coords.length - 1, Math.max(0, at))]
}

function blend(left: TraceFeature, right: TraceFeature, t: number): TraceFeature {
  const a = left.geometry?.coordinates ?? []
  const b = right.geometry?.coordinates ?? []
  const count = Math.min(a.length, b.length)
  const coordinates: number[][] = []
  for (let i = 0; i < count; i += 1) {
    const p = sample(a, i, count)
    const q = sample(b, i, count)
    coordinates.push([
      p[0] * (1 - t) + q[0] * t,
      p[1] * (1 - t) + q[1] * t,
      (p[2] ?? 0) * (1 - t) + (q[2] ?? 0) * t,
    ])
  }
  const speed = (left.properties?.speedMps ?? 0) * (1 - t) + (right.properties?.speedMps ?? 0) * t
  const min = (left.properties?.speedMinMps ?? speed) * (1 - t) + (right.properties?.speedMinMps ?? speed) * t
  const max = (left.properties?.speedMaxMps ?? speed) * (1 - t) + (right.properties?.speedMaxMps ?? speed) * t
  return {
    type: 'Feature',
    properties: {
      speedMps: speed,
      speedMinMps: min,
      speedMaxMps: max,
      displayTrace: true,
    },
    geometry: { type: 'LineString', coordinates },
  }
}

/** Solved lines plus one or two traces between neighbours that stay 8–48 m apart. */
export function densifyTraces(features: TraceFeature[], bearingDeg: number): TraceFeature[] {
  const groups = new Map<number, TraceFeature[]>()
  for (const feature of features) {
    const coords = feature.geometry?.coordinates
    if (!coords || coords.length < 4) continue
    const band = Math.round((coords[0][2] ?? 0) / 4) * 4
    const list = groups.get(band) ?? []
    list.push(feature)
    groups.set(band, list)
  }
  const out = [...features]
  for (const list of groups.values()) {
    list.sort((a, b) => {
      const a0 = a.geometry?.coordinates?.[0] ?? [0, 0]
      const b0 = b.geometry?.coordinates?.[0] ?? [0, 0]
      return crossKey(a0, bearingDeg) - crossKey(b0, bearingDeg)
    })
    for (let i = 0; i < list.length - 1; i += 1) {
      const left = list[i].geometry?.coordinates ?? []
      const right = list[i + 1].geometry?.coordinates ?? []
      const count = Math.min(left.length, right.length, 24)
      if (count < 4) continue
      let sum = 0
      for (let k = 0; k < count; k += 1) {
        sum += metres(sample(left, k, count), sample(right, k, count))
      }
      const gap = sum / count
      // Below 12 m the solved neighbours already read as a continuous band, so
      // a filler would only add entities. This keeps cardinals (seeded every
      // cell) at about the same drawn spacing as diagonals (seeded every other
      // cell), which is what the old fixed two-fillers rule broke.
      if (gap < 12 || gap > 48) continue
      // The solved field is already close together, so a wide gap takes two
      // fillers and a narrow one takes a single midpoint. Keeping the count
      // tied to the gap holds the drawn spacing near 5 m without tripling the
      // entity count on the densest bearings.
      const fillers = gap <= 20 ? [0.5] : [0.33, 0.66]
      for (const t of fillers) out.push(blend(list[i], list[i + 1], t))
    }
  }
  return out
}

/**
 * Blue in a slow part of the solved field, red in a fast part.
 *
 * `scale` is the selected 10 m wind divided by the solved inlet. The solved
 * speeds only span about 0.2–5.5 m/s, so multiplying them straight into a ramp
 * that tops out near a typhoon painted every thread the same orange and threw
 * away the wakes. The ramp is therefore anchored to that solved range with a
 * little headroom (0.5 m/s to 6.5 m/s), which leaves a NE channel amber-to-red
 * and a 1.2 m/s west channel gold-to-blue. A mild power keeps a Signal preset
 * hotter while leaving the fast and slow threads apart.
 */
export function speedColour(solvedSpeed: number, scale = 1): string {
  const bias = Math.pow(Math.max(scale, 0.25), 0.35)
  const stretched = Math.max(solvedSpeed, 0.2) * bias
  const t = Math.max(0, Math.min(1, Math.log(stretched / 0.5) / Math.log(6.5 / 0.5)))
  const stops = [
    [126, 200, 255],
    [255, 231, 168],
    [255, 176, 32],
    [226, 59, 47],
  ]
  const scaled = t * (stops.length - 1)
  const index = Math.min(stops.length - 2, Math.floor(scaled))
  const local = scaled - index
  const a = stops[index]
  const b = stops[index + 1]
  const channel = (i: number) => Math.round(a[i] * (1 - local) + b[i] * local)
  return `rgb(${channel(0)}, ${channel(1)}, ${channel(2)})`
}

/** Four speeds along a line, spanning the recorded min and max. The peak's place is not stored. */
export function speedsAlong(min: number, max: number): number[] {
  return [min, min + (max - min) * 0.65, max, min + (max - min) * 0.35]
}
