/**
 * Streamlines from the OpenFOAM channel, drawn on the 2.5D massing.
 *
 * Each line is a path integrated through the solved velocity. The colour
 * follows that path's fast and slow parts. A scale other than 1 is the
 * selected 10 m wind divided by the solved inlet: it pushes the same band
 * hotter or cooler and does not rebuild the threads. It is not a velocity
 * ratio and not a comfort threshold. The third coordinate is height above
 * the local ground; the DEM base is added here so a line sits on the same
 * floor as the extruded footprint it wraps.
 */
import {
  ArcType,
  Cartesian3,
  Color,
  ColorMaterialProperty,
  type Entity,
  type Viewer,
} from 'cesium'
import { sampleDemHeightClamped } from './demProvider'
import { densifyTraces, speedColour, speedsAlong, type TraceFeature } from './windTraces'

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
  /** Recolour the threads already on the map. A preset change must not rebuild them. */
  recolor: (scale: number) => void
}

const EMPTY: OpenfoamHandle = { dispose: () => undefined, recolor: () => undefined }

const FROM_DEG: Record<string, number> = {
  N: 0, NNE: 22.5, NE: 45, ENE: 67.5, E: 90, ESE: 112.5,
  SE: 135, SSE: 157.5, S: 180, SSW: 202.5, SW: 225, WSW: 247.5,
  W: 270, WNW: 292.5, NW: 315, NNW: 337.5,
}

export function addOpenfoamStreamlines(
  viewer: Viewer,
  collection: OpenfoamCollection | null,
  speedScale = 1,
  windFrom = 'NE',
): OpenfoamHandle {
  if (!collection || collection.features.length === 0) return EMPTY
  const traces = densifyTraces(collection.features as TraceFeature[], FROM_DEG[windFrom] ?? 45)
  const entities: Entity[] = []
  const painted: Array<{ entity: Entity; speed: number; alpha: number }> = []
  for (const feature of traces) {
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
    const mean = Number(feature.properties?.speedMps ?? 0)
    const min = Number(feature.properties?.speedMinMps ?? mean)
    const max = Number(feature.properties?.speedMaxMps ?? mean)
    const along = speedsAlong(min, max)
    const chunk = Math.max(2, Math.floor(positions.length / 3 / along.length))
    for (let part = 0; part < along.length; part += 1) {
      const start = part * chunk * 3
      const end = Math.min(positions.length, (part + 1) * chunk * 3 + 3)
      if (end - start < 6) continue
      const display = feature.properties?.displayTrace === true
      const alpha = display ? 0.78 : 0.95
      const entity = viewer.entities.add({
        name: display ? 'Wind display trace' : 'OpenFOAM streamline',
        polyline: {
          positions: Cartesian3.fromDegreesArrayHeights(positions.slice(start, end)),
          width: display ? 1.8 : 2.6,
          clampToGround: false,
          arcType: ArcType.NONE,
          material: Color.fromCssColorString(speedColour(along[part], speedScale)).withAlpha(alpha),
          // The massing is solid. The same colour when the depth test fails
          // keeps the thread visible where it passes a tower.
          depthFailMaterial: Color.fromCssColorString(speedColour(along[part], speedScale)).withAlpha(alpha),
        },
      })
      entities.push(entity)
      painted.push({ entity, speed: along[part], alpha })
    }
  }
  // Entity polylines build their geometry on a later frame. With
  // requestRenderMode a single request paints the empty frame and the
  // threads never appear until something else asks for a render.
  const repaint = () => {
    if (!viewer.isDestroyed()) viewer.scene.requestRender()
  }
  const recolor = (scale: number) => {
    for (const item of painted) {
      const graphic = item.entity.polyline
      if (!graphic) continue
      const colour = Color.fromCssColorString(speedColour(item.speed, scale)).withAlpha(item.alpha)
      graphic.material = new ColorMaterialProperty(colour)
      graphic.depthFailMaterial = new ColorMaterialProperty(colour)
    }
    repaint()
  }
  repaint()
  const timers = [window.setTimeout(repaint, 60), window.setTimeout(repaint, 280)]
  return {
    recolor,
    dispose: () => {
      for (const timer of timers) window.clearTimeout(timer)
      if (viewer.isDestroyed()) return
      for (const entity of entities) viewer.entities.remove(entity)
      viewer.scene.requestRender()
    },
  }
}
