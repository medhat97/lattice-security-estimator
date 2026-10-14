import { useState } from 'react'
import SchemeSelector from './SchemeSelector'
import { postFindParam } from '../api/estimator'
import { parseApiError } from '../api/parseError'
import type { FindParamRequest, FindParamResponse, KnownParams, Scheme, SecretDistribution, FindParam } from '../types'

const DIST_OPTIONS: { value: SecretDistribution; label: string }[] = [
  { value: 'ternary',          label: 'Ternary {−1, 0, 1}' },
  { value: 'binary',           label: 'Binary {0, 1}' },
  { value: 'gaussian',         label: 'Discrete Gaussian' },
  { value: 'uniform',          label: 'Uniform mod q' },
  { value: 'centred_binomial', label: 'Centred Binomial (Kyber-style)' },
]

const PARAM_OPTIONS: Record<Scheme, { value: FindParam; label: string; hint: string }[]> = {
  LWE: [
    { value: 'n',     label: 'n — lattice dimension',       hint: 'Find minimum n that reaches target λ' },
    { value: 'q',     label: 'q — modulus',                 hint: 'Find maximum q that still keeps target λ' },
    { value: 'sigma', label: 'σ — error std-dev',           hint: 'Find minimum σ that reaches target λ' },
  ],
  RLWE: [
    { value: 'n',     label: 'n — polynomial degree',       hint: 'Find minimum n (rounded to power of 2)' },
    { value: 'q',     label: 'q — modulus',                 hint: 'Find maximum q that still keeps target λ' },
    { value: 'sigma', label: 'σ — error std-dev',           hint: 'Find minimum σ that reaches target λ' },
  ],
  MLWE: [
    { value: 'n',     label: 'n — polynomial degree',       hint: 'Find minimum n (rounded to power of 2)' },
    { value: 'k',     label: 'k — module rank',             hint: 'Find minimum k that reaches target λ' },
    { value: 'q',     label: 'q — modulus',                 hint: 'Find maximum q that still keeps target λ' },
    { value: 'sigma', label: 'σ — error std-dev',           hint: 'Find minimum σ that reaches target λ' },
  ],
}

const PARAM_LABELS: Record<string, string> = {
  n: 'n', q: 'q', sigma: 'σ', k: 'k', eta: 'η', secret_distribution: 'Distribution',
}

// Standard defaults per scheme — shown as pre-filled hints
const SCHEME_DEFAULTS: Record<Scheme, KnownParams> = {
  LWE:  { q: 12289, sigma: 3.19, secret_distribution: 'ternary' },
  RLWE: { q: 12289, sigma: 3.19, secret_distribution: 'ternary' },
  MLWE: { n: 256, k: 2, q: 3329, eta: 3, secret_distribution: 'centred_binomial' },
}

const SIGMA_HINTS: Record<Scheme, string> = {
  LWE:  'Standard: 3.19 (academic), 2.8 (Frodo-640), 2.3 (Frodo-976)',
  RLWE: 'Standard: 3.19 (NewHope/Gaussian RLWE)',
  MLWE: 'Standard: 1.22 (Kyber-512, η=3), 1.0 (Kyber-768/1024, η=2)',
}

const Q_HINTS: Record<Scheme, string> = {
  LWE:  'Standard: 12289 (academic), 32768 (Frodo-640), 65536 (Frodo-976)',
  RLWE: 'Standard: 12289 (NewHope)',
  MLWE: 'Standard: 3329 (Kyber)',
}

function Field({ label, value, onChange, step, hint }: {
  label: string; value?: number; onChange: (v: string) => void; step?: string; hint?: string
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <input
        type="number"
        step={step}
        value={value ?? ''}
        onChange={e => onChange(e.target.value)}
        className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
      />
      {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
    </div>
  )
}

export default function ParameterFinder() {
  const [scheme, setScheme]         = useState<Scheme>('LWE')
  const [targetLambda, setTarget]   = useState<number>(128)
  const [findParam, setFindParam]   = useState<FindParam>('n')
  const [known, setKnown]           = useState<KnownParams>(SCHEME_DEFAULTS['LWE'])
  const [result, setResult]         = useState<FindParamResponse | null>(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState<string | null>(null)

  const setK = (key: keyof KnownParams, raw: string) => {
    const num = parseFloat(raw)
    setKnown(prev => ({ ...prev, [key]: isNaN(num) ? undefined : num }))
  }

  const handleSchemeChange = (s: Scheme) => {
    setScheme(s)
    setResult(null)
    setError(null)
    setKnown(SCHEME_DEFAULTS[s])
    const opts = PARAM_OPTIONS[s]
    if (!opts.find(o => o.value === findParam)) setFindParam(opts[0].value)
  }

  const handleFindParamChange = (fp: FindParam) => {
    setFindParam(fp)
    setResult(null)
    setError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    const req: FindParamRequest = { scheme, target_lambda: targetLambda, find_param: findParam, known }
    try {
      setResult(await postFindParam(req))
    } catch (ex: unknown) {
      setError(parseApiError(ex))
    } finally {
      setLoading(false)
    }
  }

  const isCB  = known.secret_distribution === 'centred_binomial'
  const opts  = PARAM_OPTIONS[scheme]
  const selectedOpt = opts.find(o => o.value === findParam) ?? opts[0]

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

      {/* Left — inputs */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-5">
        <h2 className="text-base font-semibold text-slate-700">Parameters</h2>

        <SchemeSelector value={scheme} onChange={handleSchemeChange} />

        <form onSubmit={handleSubmit} className="space-y-4">

          {/* Target λ */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Target λ — bits of security
            </label>
            <input
              type="number"
              value={targetLambda}
              onChange={e => setTarget(Number(e.target.value))}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
            />
            <p className="text-xs text-slate-400 mt-1">Common values: 80, 100, 128, 192, 256</p>
          </div>

          {/* Find which param */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Find which parameter?
            </label>
            <div className="flex flex-wrap gap-2">
              {opts.map(o => (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => handleFindParamChange(o.value)}
                  className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors border ${
                    findParam === o.value
                      ? 'bg-violet-600 text-white border-violet-600 shadow'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {o.label.split(' — ')[0]}
                </button>
              ))}
            </div>
            <p className="text-xs text-slate-400 mt-1">{selectedOpt.hint}</p>
          </div>

          <hr className="border-slate-100" />
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Known parameters</p>

          {/* Known: n */}
          {findParam !== 'n' && (
            <Field
              label="n — dimension"
              value={known.n}
              onChange={v => setK('n', v)}
              hint={scheme !== 'LWE' ? 'Must be a power of 2' : undefined}
            />
          )}

          {/* Known: k (MLWE only) */}
          {scheme === 'MLWE' && findParam !== 'k' && (
            <Field label="k — module rank" value={known.k} onChange={v => setK('k', v)} />
          )}

          {/* Known: q */}
          {findParam !== 'q' && (
            <Field label="q — modulus" value={known.q} onChange={v => setK('q', v)} hint={Q_HINTS[scheme]} />
          )}

          {/* Secret distribution */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Secret distribution</label>
            <select
              value={known.secret_distribution}
              onChange={e => setKnown(prev => ({ ...prev, secret_distribution: e.target.value as SecretDistribution }))}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
            >
              {DIST_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Error params */}
          {findParam !== 'sigma' && (
            isCB
              ? <Field label="η (eta) — centred-binomial parameter" value={known.eta} onChange={v => setK('eta', v)}
                  hint="Kyber-512: η=3 (σ≈1.22) · Kyber-768/1024: η=2 (σ=1.0)" />
              : <Field label="σ — error std-dev" value={known.sigma} onChange={v => setK('sigma', v)}
                  step="0.01" hint={SIGMA_HINTS[scheme]} />
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-violet-600 hover:bg-violet-700 disabled:bg-violet-300 text-white font-semibold py-2.5 rounded-lg transition-colors"
          >
            {loading ? 'Running…' : 'Find Parameter'}
          </button>
        </form>
      </div>

      {/* Right — results */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-700 mb-4">Result</h2>

        {!result && !loading && !error && (
          <div className="flex flex-col items-center justify-center h-64 text-slate-400 text-sm">
            <svg className="w-12 h-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Select a parameter to find and press Find Parameter
          </div>
        )}

        {loading && (
          <div className="flex flex-col items-center justify-center h-64 text-slate-500 text-sm">
            <div className="w-8 h-8 border-4 border-violet-300 border-t-violet-600 rounded-full animate-spin mb-4" />
            Running…
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
            <strong>Error:</strong> {error}
          </div>
        )}

        {result && (
          <div className="space-y-5">
            {/* Found value headline */}
            <div className="bg-violet-50 border border-violet-200 rounded-xl p-6 text-center">
              <p className="text-sm text-violet-500 font-medium mb-1">
                To achieve λ ≥ {targetLambda} bits ({scheme})
              </p>
              <p className="text-4xl font-bold text-violet-700 mb-1">
                {PARAM_LABELS[result.found_param]} = {result.found_value}
              </p>
              <p className="text-xs text-slate-500">Minimum / optimal value found</p>
            </div>

            {/* Verification */}
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">Verification</h3>
              <div className="rounded-lg border border-slate-200 overflow-hidden text-sm">
                <table className="w-full">
                  <tbody>
                    <tr className="bg-violet-50">
                      <td className="px-4 py-2 font-medium">
                        {PARAM_LABELS[result.found_param]} = {result.found_value} (found)
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-violet-700">
                        λ = {result.verification.at_found ?? '—'} bits
                      </td>
                    </tr>
                    {result.verification.at_step_below != null && (
                      <tr className="border-t border-slate-100">
                        <td className="px-4 py-2 text-slate-500">
                          {result.verification.step_below_label} (one step down)
                        </td>
                        <td className="px-4 py-2 text-right font-mono text-red-500">
                          λ = {result.verification.at_step_below} bits ✗
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Complete parameter set */}
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">Complete parameter set</h3>
              <div className="bg-slate-50 rounded-lg border border-slate-200 p-4 font-mono text-sm space-y-1">
                {Object.entries(result.parameters_complete).map(([key, val]) => (
                  <div key={key} className="flex justify-between">
                    <span className={`text-slate-500 ${key === result.found_param ? 'text-violet-700 font-bold' : ''}`}>
                      {PARAM_LABELS[key] ?? key}
                    </span>
                    <span className={key === result.found_param ? 'text-violet-700 font-bold' : 'text-slate-700'}>
                      {String(val)}
                      {key === result.found_param && ' ◀ found'}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Warnings */}
            {result.warnings.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-xs font-semibold text-yellow-700 mb-1">Modelling notes</p>
                {result.warnings.map((w, i) => (
                  <p key={i} className="text-xs text-yellow-700">• {w}</p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
