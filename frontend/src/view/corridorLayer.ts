/**
 * The prevailing-wind corridor, drawn as what it is: a line.
 *
 * The corridor is a least-cost through-route over the frontal-area cost surface
 * (`services/ventilation.py`). It is **geometry**, not flow — no speed, no
 * turbulence, no velocity ratio — and the panel that switches it on says so. The
 * drawing therefore uses a plain clamped polyline with a soft underlay, not a
 * colour ramp that would imply a magnitude.
 *
 * A separate module from `interventionLayer` because a corridor is not an
 * intervention: it is a diagnostic derived from the massing, it is never picked
 * or edited, and it must survive a sandbox refresh.
 */
import {
  Cartesian3,
  Color,
  type Entity,
  type Viewer,
} from 'cesium'

export interface CorridorHandle {
  dispose: () => void
}

const EMPTY: CorridorHandle = { dispose: () => undefined }

export function addCorridor(
  viewer: Viewer,
  line: { type: 'LineString'; coordinates: number[][] } | null,
): CorridorHandle {
  if (!line || line.coordinates.length < 2) return EMPTY

  const positions = line.coordinates
    .filter((point) => Array.isArray(point) && point.length >= 2)
    .flatMap(([lon, lat]) => [Number(lon), Number(lat)])
  if (positions.length < 4) return EMPTY

  const cartesians = Cartesian3.fromDegreesArray(positions)
  const entities: Entity[] = [
    // Soft underlay first so the bright line reads on both the photo basemap
    // and the dark tactical mode.
    viewer.entities.add({
      name: 'Ventilation corridor (halo)',
      polyline: {
        positions: cartesians,
        width: 13,
        clampToGround: true,
        material: Color.fromCssColorString('#5cff9d').withAlpha(0.16),
      },
    }),
    viewer.entities.add({
      name: 'Ventilation corridor (NE)',
      polyline: {
        positions: cartesians,
        width: 3.5,
        clampToGround: true,
        material: Color.fromCssColorString('#5cff9d').withAlpha(0.95),
      },
    }),
    // End ticks: a line alone does not say which way the wind enters.
    viewer.entities.add({
      position: cartesians[0],
      point: {
        pixelSize: 7,
        color: Color.fromCssColorString('#5cff9d'),
        outlineColor: Color.fromCssColorString('#082015'),
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    }),
  ]

  viewer.scene.requestRender()

  return {
    dispose: () => {
      if (viewer.isDestroyed()) return
      for (const entity of entities) viewer.entities.remove(entity)
      viewer.scene.requestRender()
    },
  }
}
