import type { TideState } from '@/api/types'

export interface TypedRainfall {
  precipitation: number
  durationHours: number
  tideState: TideState
}

/** Slider values from before a gauge took over. Moving a water slider clears it. */
let typedSnapshot: TypedRainfall | null = null

export function rememberTypedRainfall(value: TypedRainfall): void {
  if (!typedSnapshot) typedSnapshot = value
}

export function peekTypedRainfall(): TypedRainfall | null {
  return typedSnapshot
}

export function takeTypedRainfall(): TypedRainfall | null {
  const previous = typedSnapshot
  typedSnapshot = null
  return previous
}

export function forgetTypedRainfall(): void {
  typedSnapshot = null
}
