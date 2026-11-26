/**
 * Unit tests for the API error normaliser.
 *
 * The backend emits two error shapes because the spec mandates both: a FastAPI
 * `detail` and an `{"error": {"code", "message", "details"}}` envelope. This module
 * collapses them into one `ApiError` so callers have a single branch. If the
 * precedence between the two is wrong, every error message in the panel is wrong --
 * and it would fail silently, because a wrong-but-plausible string still renders.
 */
import { describe, expect, it, vi } from 'vitest'
import { AxiosError } from 'axios'

import { ApiError, errorMessage, toApiError, apiUrl, serverUrl } from './client'

/** An AxiosError carrying a backend response, or none at all for a network failure. */
const fromResponse = (status: number, data: unknown): AxiosError =>
  new AxiosError('Request failed', 'ERR_BAD_REQUEST', undefined, undefined, {
    status,
    data,
  } as never)

const withBody = (data: unknown): AxiosError => fromResponse(400, data)

describe('toApiError', () => {
  it('prefers the structured envelope over FastAPI detail', () => {
    const err = toApiError(
      withBody({
        detail: 'a fastapi message',
        error: { code: 'VALIDATION', message: 'the real message', details: { field: 1 } },
      }),
    )
    expect(err.message).toBe('the real message')
    expect(err.code).toBe('VALIDATION')
    expect(err.status).toBe(400)
    expect(err.details).toEqual({ field: 1 })
  })

  it('falls back to FastAPI detail when there is no envelope', () => {
    const err = toApiError(withBody({ detail: 'plain fastapi message' }))
    expect(err.message).toBe('plain fastapi message')
    expect(err.code).toBe('HTTP_400')
  })

  it('synthesises a code when the body carries neither shape', () => {
    const err = toApiError(withBody({}))
    expect(err.code).toBe('HTTP_400')
    expect(err.status).toBe(400)
  })

  it('treats a network failure as status 0 rather than throwing', () => {
    // No `response` at all: the backend is down, DNS failed, or the request was
    // aborted. Reading `error.response.status` unguarded is the classic crash here,
    // and it would replace a useful message with a blank screen.
    const err = toApiError(new AxiosError('Network Error', 'ERR_NETWORK'))
    expect(err.status).toBe(0)
    expect(err.code).toBe('NETWORK')
    expect(err.message).toBe('Network Error')
  })

  it('passes a non-axios error through with its own message', () => {
    const err = toApiError(new Error('boom'))
    expect(err).toBeInstanceOf(ApiError)
    expect(err.message).toBe('boom')
    expect(err.code).toBe('NETWORK')
  })

  it('handles a completely unknown value without throwing', () => {
    const err = toApiError('a bare string')
    expect(err).toBeInstanceOf(ApiError)
    expect(err.message).toBe('a bare string')
  })

  it('preserves a 5xx status so callers can tell server from validation', () => {
    expect(toApiError(fromResponse(503, { detail: 'unavailable' })).status).toBe(503)
    expect(toApiError(fromResponse(404, { detail: 'missing' })).status).toBe(404)
  })
})

describe('errorMessage', () => {
  it('passes an ApiError message straight through', () => {
    expect(errorMessage(new ApiError('scene not found', 404, 'NOT_FOUND'))).toBe(
      'scene not found',
    )
  })
  it('stringifies anything else rather than throwing', () => {
    // This is what an error boundary calls. Throwing here would replace a readable
    // failure with a blank page.
    expect(errorMessage('raw string')).toBe('raw string')
    expect(errorMessage(undefined)).toBe('undefined')
  })
})

/**
 * URL resolution, which no unit test covered and which a proxy made invisible.
 *
 * `vitest` runs with `VITE_API_BASE_URL` unset, so these assert the dev shape:
 * every path stays root-relative, which the Vite proxy forwards to port 8000.
 * That is exactly why the production failure survived: the same code is correct
 * here and a 404 there.
 *
 * The split-deployment case is what the assertions below pin by construction --
 * `apiUrl` and `serverUrl` both derive from the one configured base, so if
 * either ever drops back to a hardcoded '/api/...' or '/static/...', it is no
 * longer reading from `API_BASE_URL` and this file is where to add the case.
 */
describe('apiUrl and serverUrl', () => {
  it('keeps /api paths root-relative when no base is configured', () => {
    expect(apiUrl('/scenes/s1/chat/stream')).toBe('/api/scenes/s1/chat/stream')
  })

  it('keeps non-/api backend paths root-relative when no base is configured', () => {
    // Both go through the Vite proxy in dev: /health and /static are in
    // vite.config.ts's proxy table, not just /api.
    expect(serverUrl('/health')).toBe('/health')
    expect(serverUrl('/static/openfoam/wind_index.json')).toBe(
      '/static/openfoam/wind_index.json',
    )
  })

  it('does not double the slash or the /api segment', () => {
    expect(apiUrl('/scenes')).toBe('/api/scenes')
    expect(serverUrl('/health')).toBe('/health')
  })

  /**
   * The production shape, which is the one that failed. A split deployment sets
   * `VITE_API_BASE_URL` to an absolute origin; both helpers must then leave the
   * frontend's own origin entirely, because the static host serves neither
   * `/api` nor `/static` and `/health` is not a file.
   *
   * `vi.resetModules()` is required: the base is a module-level const, so
   * stubbing the env after import would test nothing.
   */
  it('resolves against the configured origin when the API is on another host', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com/api')
    vi.resetModules()
    const mod = await import('./client')

    expect(mod.apiUrl('/scenes/s1/chat/stream')).toBe(
      'https://api.example.com/api/scenes/s1/chat/stream',
    )
    expect(mod.serverUrl('/health')).toBe('https://api.example.com/health')
    expect(mod.serverUrl('/static/openfoam/wind_index.json')).toBe(
      'https://api.example.com/static/openfoam/wind_index.json',
    )

    vi.unstubAllEnvs()
    vi.resetModules()
  })
})
