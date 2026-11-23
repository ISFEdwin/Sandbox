/**
 * The prevailing-wind corridor, drawn in the streamline style of a pedestrian
 * wind study: a sheet of thin gold threads along the through-route, crimson
 * threads where the massing forms a narrow gap, blue threads where a tall
 * face steps down to a lower one, and pale threads at an exposed corner.
 *
 * The corridor is still the least-cost route on the frontal-area surface
 * (`services/ventilation.py`). The colours name those geometric patterns.
 * They are not a wind speed, not a turbulence intensity, and not a velocity
 * ratio. Nothing here samples a flow field.
 *
 * A separate module from `interventionLayer` because a corridor is not an
 * intervention: it is a diagnostic derived from the massing, it is never picked
 * or edited, and it must survive a sandbox refresh.
 */
import {
  ArcType,
  Cartesian2,
  Cartesian3,
  Cartographic,
  Color,
  EllipsoidTerrainProvider,
  HeightReference,
  LabelStyle,
  sampleTerrainMostDetailed,
  type Entity,
  type Viewer,
} from 'cesium'

export interface CorridorEffect {
  labels?: string[]
  at: number[]
}

export interface CorridorLine {
  type: 'LineString'
  coordinates: number[][]
  properties?: {
    geometricEffects?: CorridorEffect[]
    sidecar?: { status?: string; method?: string; limitation?: string }
  }
}

export interface CorridorHandle {
  dispose: () => void
}

const EMPTY: CorridorHandle = { dispose: () => undefined }

const M_PER_DEG_LAT = 110_540

/** One thread in the bundle. Offsets are metres; height is metres above ground. */
interface Strand {
  lateral: number
  height: number
  /** Extra lateral drift, metres, applied toward the end of a short run. */
  drift: number
  wave: number
  phase: number
  color: string
  alpha: number
  width: number
}

/**
 * The ground sheet. Warm gold and amber, low, slightly waved, spread a few
 * metres either side of the route. This is the carpet of threads in the
 * reference picture.
 */
const SHEET: Strand[] = [
  { lateral: -32, height: 3, drift: 0, wave: 4.5, phase: 0.2, color: '#ffd36a', alpha: 0.55, width: 1.8 },
  { lateral: -22, height: 8, drift: 0, wave: 3.2, phase: 1.4, color: '#ffb020', alpha: 0.75, width: 2.1 },
  { lateral: -14, height: 5, drift: 0, wave: 2.4, phase: 2.2, color: '#ffe7a8', alpha: 0.5, width: 1.5 },
  { lateral: -7, height: 12, drift: 0, wave: 2.0, phase: 0.7, color: '#ff8c1a', alpha: 0.9, width: 2.6 },
  { lateral: -2, height: 6, drift: 0, wave: 1.6, phase: 1.9, color: '#fff1c4', alpha: 0.62, width: 1.6 },
  { lateral: 4, height: 16, drift: 0, wave: 2.8, phase: 0.4, color: '#ff6a1a', alpha: 0.78, width: 2.2 },
  { lateral: 10, height: 9, drift: 0, wave: 3.4, phase: 2.6, color: '#ffb020', alpha: 0.7, width: 1.9 },
  { lateral: 18, height: 22, drift: 0, wave: 2.2, phase: 1.1, color: '#e8872a', alpha: 0.55, width: 1.6 },
  { lateral: 26, height: 7, drift: 0, wave: 4.0, phase: 0.9, color: '#ffd36a', alpha: 0.48, width: 1.7 },
  { lateral: 34, height: 4, drift: 0, wave: 3.0, phase: 2.8, color: '#ffe7a8', alpha: 0.4, width: 1.5 },
]

/** Narrow-gap pattern: a tight crimson bundle, a little higher than the sheet. */
const VENTURI: Strand[] = [
  { lateral: -3, height: 16, drift: 0, wave: 0.6, phase: 0.4, color: '#d31212', alpha: 0.92, width: 1.8 },
  { lateral: 0, height: 22, drift: 0, wave: 0.4, phase: 1.2, color: '#ff3b2f', alpha: 0.85, width: 1.45 },
  { lateral: 3, height: 18, drift: 0, wave: 0.8, phase: 2.1, color: '#ff6a45', alpha: 0.75, width: 1.2 },
]

/** Downwash pattern: cooler threads that peel outward and upward. */
const DOWNWASH: Strand[] = [
  { lateral: -10, height: 26, drift: -12, wave: 3.5, phase: 0.3, color: '#3aa0ff', alpha: 0.7, width: 1.15 },
  { lateral: 12, height: 32, drift: 14, wave: 4.2, phase: 1.5, color: '#7ec8ff', alpha: 0.55, width: 1.05 },
  { lateral: -4, height: 20, drift: -6, wave: 2.4, phase: 2.2, color: '#d6ecff', alpha: 0.42, width: 1.0 },
]

/** Corner pattern: short pale filaments beside the route. */
const CORNER: Strand[] = [
  { lateral: -8, height: 13, drift: -4, wave: 1.1, phase: 0.5, color: '#f7f4ef', alpha: 0.72, width: 1.05 },
  { lateral: 8, height: 15, drift: 4, wave: 1.4, phase: 1.8, color: '#ffe9a8', alpha: 0.55, width: 1.0 },
]

interface LonLat {
  lon: number
  lat: number
}

function metresPerDegreeLon(lat: number): number {
  return 111_320 * Math.cos((lat * Math.PI) / 180)
}

function offsetPoint(origin: LonLat, eastM: number, northM: number): LonLat {
  const mLon = metresPerDegreeLon(origin.lat)
  return {
    lon: origin.lon + eastM / mLon,
    lat: origin.lat + northM / M_PER_DEG_LAT,
  }
}

function tangent(path: LonLat[], index: number): { east: number; north: number } {
  const a = path[Math.max(0, index - 1)]
  const b = path[Math.min(path.length - 1, index + 1)]
  const mLon = metresPerDegreeLon((a.lat + b.lat) / 2)
  let east = (b.lon - a.lon) * mLon
  let north = (b.lat - a.lat) * M_PER_DEG_LAT
  const length = Math.hypot(east, north)
  if (length < 1e-6) return { east: 1, north: 0 }
  east /= length
  north /= length
  return { east, north }
}

/** A thread following `path`, shifted sideways and waved. Deterministic. */
function strandPath(path: LonLat[], strand: Strand): LonLat[] {
  const last = Math.max(1, path.length - 1)
  return path.map((point, index) => {
    const heading = tangent(path, index)
    // Left of the direction of travel.
    const leftEast = -heading.north
    const leftNorth = heading.east
    const along = index / last
    const lateral = strand.lateral + strand.drift * along + strand.wave * Math.sin(index * 0.45 + strand.phase)
    return offsetPoint(point, leftEast * lateral, leftNorth * lateral)
  })
}

function toCartesians(path: LonLat[], ground: number[], clearance: number): Cartesian3[] {
  return path.map((point, index) =>
    Cartesian3.fromDegrees(point.lon, point.lat, (ground[index] ?? 0) + clearance),
  )
}

function withinMetres(a: LonLat, b: LonLat, metres: number): boolean {
  const mLon = metresPerDegreeLon((a.lat + b.lat) / 2)
  const east = (a.lon - b.lon) * mLon
  const north = (a.lat - b.lat) * M_PER_DEG_LAT
  return east * east + north * north <= metres * metres
}

/** Inclusive-exclusive index spans of the route that carry one pattern label. */
function patternSpans(path: LonLat[], effects: CorridorEffect[], label: string): Array<[number, number]> {
  const marked = path.map((point) =>
    effects.some((effect) => {
      const at = effect.at
      if (!at || at.length < 2) return false
      if (!(effect.labels ?? []).includes(label)) return false
      return withinMetres(point, { lon: at[0], lat: at[1] }, 18)
    }),
  )
  const spans: Array<[number, number]> = []
  let start = -1
  for (let i = 0; i <= path.length; i += 1) {
    if (i < path.length && marked[i]) {
      if (start < 0) start = i
    } else if (start >= 0) {
      const from = Math.max(0, start - 1)
      const to = Math.min(path.length, i + 1)
      if (to - from >= 2) spans.push([from, to])
      start = -1
    }
  }
  return spans
}

async function groundHeights(viewer: Viewer, path: LonLat[]): Promise<number[]> {
  const provider = viewer.terrainProvider
  if (!provider || provider instanceof EllipsoidTerrainProvider) {
    return path.map(() => 0)
  }
  const cartographics = path.map((point) => Cartographic.fromDegrees(point.lon, point.lat))
  try {
    const sampled = await sampleTerrainMostDetailed(provider, cartographics)
    return sampled.map((carto) => (Number.isFinite(carto.height) ? carto.height : 0))
  } catch {
    return path.map(() => 0)
  }
}

export function addCorridor(viewer: Viewer, line: CorridorLine | null): CorridorHandle {
  if (!line || line.coordinates.length < 2) return EMPTY

  const path: LonLat[] = line.coordinates
    .filter((point) => Array.isArray(point) && point.length >= 2)
    .map(([lon, lat]) => ({ lon: Number(lon), lat: Number(lat) }))
    .filter((point) => Number.isFinite(point.lon) && Number.isFinite(point.lat))
  if (path.length < 2) return EMPTY

  const effects = line.properties?.geometricEffects ?? []
  const threads: Entity[] = []
  const labels: Entity[] = []
  let disposed = false

  const paint = (ground: number[]) => {
    if (disposed || viewer.isDestroyed()) return
    const place = (points: LonLat[], heights: number[], strand: Strand) => {
      threads.push(
        viewer.entities.add({
          name: 'Wind corridor streamline',
          polyline: {
            positions: toCartesians(strandPath(points, strand), heights, strand.height + 2),
            width: strand.width,
            clampToGround: false,
            arcType: ArcType.GEODESIC,
            material: Color.fromCssColorString(strand.color).withAlpha(strand.alpha),
          },
        }),
      )
    }

    for (const strand of SHEET) place(path, ground, strand)
    const families: Array<[string, Strand[]]> = [
      ['Venturi acceleration', VENTURI],
      ['downwash risk', DOWNWASH],
      ['corner acceleration', CORNER],
    ]
    for (const [label, strands] of families) {
      for (const [from, to] of patternSpans(path, effects, label)) {
        const slice = path.slice(from, to)
        const sliceGround = ground.slice(from, to)
        for (const strand of strands) place(slice, sliceGround, strand)
      }
    }
    viewer.scene.requestRender()
  }

  // Draw at once so the channel is visible before the terrain sample returns,
  // then lift the same threads onto the ground heights.
  paint(path.map(() => 0))

  void groundHeights(viewer, path).then((heights) => {
    if (disposed || viewer.isDestroyed()) return
    if (heights.every((height) => height === 0)) return
    for (const entity of threads) viewer.entities.remove(entity)
    threads.length = 0
    paint(heights)
  })

  const seen = new Set<string>()
  for (const effect of effects) {
    const [lon, lat] = effect.at ?? []
    if (lon == null || lat == null) continue
    for (const label of effect.labels ?? []) {
      if (seen.has(label)) continue
      seen.add(label)
      labels.push(
        viewer.entities.add({
          position: Cartesian3.fromDegrees(lon, lat, 24),
          label: {
            text: label,
            font: '12px sans-serif',
            fillColor: Color.fromCssColorString('#fff6e8'),
            outlineColor: Color.fromCssColorString('#1a120c'),
            outlineWidth: 3,
            style: LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new Cartesian2(0, -18),
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
            heightReference: HeightReference.CLAMP_TO_GROUND,
          },
        }),
      )
    }
  }

  return {
    dispose: () => {
      disposed = true
      if (viewer.isDestroyed()) return
      for (const entity of threads) viewer.entities.remove(entity)
      for (const entity of labels) viewer.entities.remove(entity)
      viewer.scene.requestRender()
    },
  }
}
