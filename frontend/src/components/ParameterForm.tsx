import { useEffect, useState } from 'react'
import type { EstimateRequest, Preset, Scheme, SecretDistribution } from '../types'

interface Props {
  scheme: Scheme
  presets: Preset[]
  onSubmit: (req: EstimateRequest) => void
  loading: boolean
}

const DIST_OPTIONS: { value: SecretDistribution; label: string }[] = [
  { value: 'ternary',          label: 'Ternary {−1, 0, 1}' },
  { value: 'binary',           label: 'Binary {0, 1}' },
  { value: 'gaussian',         label: 'Discrete Gaussian' },
  { value: 'uniform',          label: 'Uniform mod q' },
  { value: 'centred_binomial', label: 'Centred Binomial (Kyber-style)' },
]

const DEFAULT: EstimateRequest = {
  scheme: 'LWE',
  n: 512,
  q: 12289,
  sigma: 3.19,
  secret_distribution: 'ternary',
}

function Field({
  label, value, onChange, type = 'number', step, hint,
}: {
  label: string
  value: string | number | undefined
  onChange: (v: string) => void
  type?: string
  step?: string
  hint?: string
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <input
        type={type}
        step={step}
        value={value ?? ''}
        onChange={e => onChange(e.target.value)}
        className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />
      {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
    </div>
  )
}

export default function ParameterForm({ scheme, presets, onSubmit, loading }: Props) {
  const [form, setForm]           = useState<EstimateRequest>({ ...DEFAULT, scheme })
  const [useSigma, setUseSigma]   = useState(true)
  const [selectedPreset, setSelectedPreset] = useState<string>('')

  useEffect(() => {
    setForm(prev => ({ ...prev, scheme }))
    setSelectedPreset('')
  }, [scheme])

  const detectPreset = (updated: EstimateRequest) => {
    const match = presets.find(p =>
      p.scheme === updated.scheme &&
      p.n === updated.n &&
      p.q === updated.q &&
      (p.sigma ?? undefined) === updated.sigma &&
      (p.eta ?? undefined) === updated.eta &&
      (p.k ?? undefined) === updated.k &&
      p.secret_distribution === updated.secret_distribution
    )
    setSelectedPreset(match ? match.name : '')
  }

  const set = (key: keyof EstimateRequest, raw: string) => {
    const num = parseFloat(raw)
    const updated = { ...form, [key]: isNaN(num) ? undefined : num }
    setForm(updated)
    detectPreset(updated)
  }

  const applyPreset = (name: string) => {
    const p = presets.find(x => x.name === name)
    if (!p) return
    const updated: EstimateRequest = {
      scheme: p.scheme,
      n: p.n,
      q: p.q,
      sigma: p.sigma ?? undefined,
      eta: p.eta ?? undefined,
      k: p.k ?? undefined,
      secret_distribution: p.secret_distribution,
    }
    setForm(updated)
    setUseSigma(p.sigma != null)
    setSelectedPreset(name)
  }

  const handleDistChange = (val: SecretDistribution) => {
    const updated = { ...form, secret_distribution: val }
    setForm(updated)
    detectPreset(updated)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const req: EstimateRequest = { ...form }
    if (!useSigma) { delete req.sigma } else { delete req.alpha }
    onSubmit(req)
  }

  const isCB = form.secret_distribution === 'centred_binomial'

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Presets */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Load preset</label>
        <select
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          value={selectedPreset}
          onChange={e => applyPreset(e.target.value)}
        >
          <option value="">— Custom {scheme} —</option>
          {presets
            .filter(p => p.scheme === scheme)
            .map(p => (
              <option key={p.name} value={p.name}>{p.name}</option>
            ))}
        </select>
      </div>

      <hr className="border-slate-200" />

      {/* Common fields */}
      <div className="grid grid-cols-2 gap-4">
        <Field label="n — dimension" value={form.n} onChange={v => set('n', v)} hint={scheme !== 'LWE' ? 'Must be a power of 2' : undefined} />
        <Field label="q — modulus" value={form.q} onChange={v => set('q', v)} />
      </div>

      {scheme === 'MLWE' && (
        <Field label="k — module rank" value={form.k} onChange={v => set('k', v)} hint="Effective dimension = n × k" />
      )}

      {/* Secret distribution */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Secret distribution</label>
        <select
          value={form.secret_distribution}
          onChange={e => handleDistChange(e.target.value as SecretDistribution)}
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          {DIST_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Error parameters */}
      {isCB ? (
        <Field label="η (eta) — centred-binomial parameter" value={form.eta} onChange={v => set('eta', v)} hint="σ ≈ √(η/2)" />
      ) : (
        <div className="space-y-3">
          <div className="flex gap-4 text-sm">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="radio" checked={useSigma} onChange={() => { setUseSigma(true); detectPreset(form) }} />
              Use σ (sigma)
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="radio" checked={!useSigma} onChange={() => { setUseSigma(false); detectPreset(form) }} />
              Use α (alpha = σ/q)
            </label>
          </div>
          {useSigma
            ? <Field label="σ — error standard deviation" value={form.sigma} onChange={v => set('sigma', v)} step="0.01" />
            : <Field label="α — error rate (σ/q)" value={form.alpha} onChange={v => set('alpha', v)} step="0.000001" />
          }
        </div>
      )}

      {/* Optional samples */}
      <Field
        label="m — number of samples (optional)"
        value={form.m}
        onChange={v => set('m', v)}
        hint="Leave empty to use the estimator default (unlimited)"
      />

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white font-semibold py-2.5 rounded-lg transition-colors"
      >
        {loading ? 'Running…' : 'Estimate Security'}
      </button>
    </form>
  )
}
