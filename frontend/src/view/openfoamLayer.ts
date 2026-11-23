/**
 * Streamlines from the OpenFOAM channel, drawn on the 2.5D massing.
 *
 * Each line is a path integrated through the solved velocity. The colour is
 * the mean speed along that path, in m/s, from that coarse RANS run. A scale
 * other than 1 multiplies those speeds by the ratio of two PlanD inlets when
 * the selected table was not the one that was solved. It is
 * not a velocity ratio and not a comfort threshold. The third coordinate is
 * height above the local ground; the DEM base is added here so a line sits
 * on the same floor as the extruded footprint it wraps.
 */
import {
  ArcType,
  Cartesian3,
  Color,
  type Entity,
  type Viewer,
} from 'cesium'
import { sampleDemHeightClamped } from './demProvider'

export interface OpenfoamCollection {
  type: 'FeatureCollection'
  features: Array<{
    type: 'Feature'
    properties?: { speedMps?: number }
    geometry?: { type: string; coordinates?: number[][] }
  }>
  properties?: {
    inletNote?: string
    inletSpeedMps?: number
  }
}

export interface OpenfoamHandle {
  dispose: () => void
}

const EMPTY: OpenfoamHandle = { dispose: () => undefined }

/** Display bins for the solved speed. The breaks are stated, not a criterion. */
function speedColour(speed: number): string {
  if (speed < 1) return '#7ec8ff'
  if (speed < 2) return '#ffe7a8'
  if (speed < 3.5) return '#ffb020'
  return '#e23b2f'
}

export function addOpenfoamStreamlines(
  viewer: Viewer,
  collection: OpenfoamCollection | null,
  speedScale = 1,
): OpenfoamHandle {
  if (!collection || collection.features.length === 0) return EMPTY
  const entities: Entity[] = []
  for (const feature of collection.features) {
    const coords = feature.geometry?.coordinates
    if (!coords || coords.length < 2) continue
    const positions: number[] = []
    for (const point of coords) {
      if (point.length < 2) continue
      const [lon, lat, agl] = point
      const ground = sampleDemHeightClamped(lon, lat) ?? 0
      positions.push(lon, lat, ground + (agl ?? 0))
    }
    if (positions.length < 6) continue
    const speed = Number(feature.properties?.speedMps ?? 0) * speedScale
    entities.push(
      viewer.entities.add({
        name: 'OpenFOAM streamline',
        polyline: {
          positions: Cartesian3.fromDegreesArrayHeights(positions),
          width: 1.6,
          clampToGround: false,
          arcType: ArcType.NONE,
          material: Color.fromCssColorString(speedColour(speed)).withAlpha(0.9),
        },
      }),
    )
  }
  viewer.scene.requestRender()
  return {
    dispose: () => {
      if (viewer.isDestroyed()) return
      for (const entity of entities) viewer.entities.remove(entity)
      viewer.scene.requestRender()
    },
  }
}
