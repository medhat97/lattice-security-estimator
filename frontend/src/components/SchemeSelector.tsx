import type { Scheme } from '../types'

interface Props {
  value: Scheme
  onChange: (s: Scheme) => void
}

const SCHEMES: Scheme[] = ['LWE', 'RLWE', 'MLWE']

const DESCRIPTIONS: Record<Scheme, string> = {
  LWE:  'Learning With Errors — plain integer lattice (Regev 2005)',
  RLWE: 'Ring-LWE — polynomial ring ℤq[x]/(xⁿ+1)',
  MLWE: 'Module-LWE — module over the ring (Kyber, Dilithium)',
}

export default function SchemeSelector({ value, onChange }: Props) {
  return (
    <div className="mb-6">
      <div className="flex gap-2 mb-2">
        {SCHEMES.map(s => (
          <button
            key={s}
            onClick={() => onChange(s)}
            className={`px-5 py-2 rounded-lg font-semibold text-sm transition-colors ${
              value === s
                ? 'bg-indigo-600 text-white shadow'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            {s}
          </button>
        ))}
      </div>
      <p className="text-sm text-slate-500">{DESCRIPTIONS[value]}</p>
    </div>
  )
}
