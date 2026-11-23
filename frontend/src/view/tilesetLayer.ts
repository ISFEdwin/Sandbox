/**
 * 3D Tiles layer — real textured building meshes and terrain from 6-NW-12D.
 *
 * The buildings and terrain(TB) tilesets carry no root.transform (their vertices
 * are in HK1980 metre grid).  Pass a modelMatrix from hk1980Transform so Cesium
 * positions them correctly in ECEF.
 */
import { Cesium3DTileset, Matrix4, type Viewer } from 'cesium'

import { useTileLoadStore, type TilesetName } from '@/state/tileLoadStore'

export interface TilesetHandle {
  tileset: Cesium3DTileset
  dispose: () => void
}

export interface TilesetOptions {
  /** 4×4 model matrix applied after load (e.g. HK1980 → ECEF). */
  modelMatrix?: Matrix4
  /**
   * Maximum screen-space error threshold.
   * 16 is a good starting point for multi-LOD tilesets; lower values load more
   * detail, higher values load less.  The old single-tile default was 1.
   */
  maximumScreenSpaceError?: number
  /** Reported to the loading screen. */
  name?: TilesetName
  /**
   * Load fewer, coarser tiles. The city tileset's only content is the dense
   * Draco leaf (no parent mesh), so a close orbit otherwise requests every
   * leaf. This skips siblings, culls requests while the camera is moving, and
   * lets screen-space error rise away from the centre of the view.
   */
  lighter?: boolean
}

/**
 * Load a 3D Tiles tileset from a URL and add it to the scene.
 *
 * Failure is logged rather than thrown: a missing or malformed tileset must not
 * take the scene down, exactly like a missing city model or waterbody layer.
 */
export async function add3DTileset(
  viewer: Viewer,
  url: string,
  options: TilesetOptions = {},
): Promise<TilesetHandle | null> {
  if (viewer.isDestroyed()) return null

  const { modelMatrix, maximumScreenSpaceError = 16, name, lighter = false } = options
  const report = name ? useTileLoadStore.getState() : null
  if (name) report?.set(name, 'loading')

  try {
    const tileset = await Cesium3DTileset.fromUrl(url, {
      maximumScreenSpaceError,
      // The terrain mesh is one small tileset and should stay put while the
      // camera moves. The city mesh is the opposite: hundreds of dense leaves
      // and no coarser body, so holding every request until the camera settles,
      // and not fetching siblings off to the side, is what keeps an orbit from
      // stalling on geometry the view does not need yet.
      dynamicScreenSpaceError: lighter,
      foveatedScreenSpaceError: lighter,
      foveatedConeSize: lighter ? 0.25 : 1,
      cullRequestsWhileMoving: lighter,
      cullRequestsWhileMovingMultiplier: lighter ? 60 : 60,
      progressiveResolutionHeightFraction: lighter ? 0.35 : 0.5,
      skipLevelOfDetail: lighter,
      baseScreenSpaceError: lighter ? 1024 : 1024,
      skipScreenSpaceErrorFactor: lighter ? 16 : 16,
      immediatelyLoadDesiredLevelOfDetail: lighter,
      loadSiblings: !lighter,
      cacheBytes: (lighter ? 128 : 768) * 1024 * 1024,
      maximumCacheOverflowBytes: (lighter ? 64 : 512) * 1024 * 1024,
    })
    if (viewer.isDestroyed()) {
      tileset.destroy()
      return null
    }

    if (name) {
      // `initialTilesLoaded` fires once, when everything the first view needs is in.
      tileset.initialTilesLoaded.addEventListener(() => useTileLoadStore.getState().set(name, 'ready'))
      tileset.loadProgress.addEventListener((pending: number, processing: number) =>
        useTileLoadStore.getState().setPending(name, pending + processing),
      )
    }

    if (modelMatrix) {
      tileset.modelMatrix = Matrix4.clone(modelMatrix)
    }

    tileset.allTilesLoaded.addEventListener(() => {
      if (!viewer.isDestroyed()) viewer.scene.requestRender()
    })

    // requestRenderMode suppresses automatic redraws; each batch of tiles that
    // arrives needs an explicit frame request or it sits in the primitive list
    // but never paints.
    tileset.tileLoad.addEventListener(() => {
      if (!viewer.isDestroyed()) viewer.scene.requestRender()
    })

    tileset.tileFailed.addEventListener((event) => {
      console.error('[3dtiles] tile failed:', event)
    })

    viewer.scene.primitives.add(tileset)
    viewer.scene.requestRender()
    return {
      tileset,
      dispose: () => {
        if (name) useTileLoadStore.getState().reset(name)
        if (!viewer.isDestroyed()) {
          viewer.scene.primitives.remove(tileset)
        } else {
          tileset.destroy()
        }
      },
    }
  } catch (err) {
    console.warn('[3dtiles] failed to load tileset:', err)
    if (name) useTileLoadStore.getState().set(name, 'failed')
    return null
  }
}
