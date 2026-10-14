import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import type { EstimateResponse } from '../types'

interface Props {
  result: EstimateResponse
}

function SecurityBadge({ bits }: { bits: number }) {
  const { label, color } =
    bits >= 256 ? { label: '256-bit secure', color: 'bg-green-100 text-green-800 border-green-300' }
    : bits >= 192 ? { label: '192-bit secure', color: 'bg-green-100 text-green-800 border-green-300' }
    : bits >= 128 ? { label: '128-bit secure', color: 'bg-green-100 text-green-800 border-green-300' }
    : bits >= 80  ? { label: 'Below 128-bit', color: 'bg-yellow-100 text-yellow-800 border-yellow-300' }
    : { label: 'Insecure (< 80 bit)', color: 'bg-red-100 text-red-800 border-red-300' }

  return (
    <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold border ${color}`}>
      {label}
    </span>
  )
}

const ATTACK_LABELS: Record<string, string> = {
  primal_usvp: 'Primal USVP',
  dual_hybrid:  'Dual Hybrid',
  primal_bdd:   'Primal BDD',
}

const COLORS = ['#6366f1', '#f59e0b', '#10b981']

export default function ResultsPanel({ result }: Props) {
  const attacks = Object.entries(result.attacks)

  // Build chart data: one point per attack showing its cost
  const chartData = attacks
    .filter(([, v]) => v.rop_log2 != null)
    .map(([name, v]) => ({
      name: ATTACK_LABELS[name] ?? name,
      'log₂(cost)': v.rop_log2,
      β: v.beta ?? null,
    }))

  return (
    <div className="space-y-6">
      {/* Lambda headline */}
      <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-6 text-center">
        <p className="text-sm text-indigo-500 font-medium mb-1">Estimated Security Level</p>
        <p className="text-5xl font-bold text-indigo-700 mb-2">
          {result.lambda_bits.toFixed(1)}
          <span className="text-2xl ml-2 font-normal">bits</span>
        </p>
        <SecurityBadge bits={result.lambda_bits} />
        <p className="text-xs text-slate-500 mt-3">
          Dominant attack: <strong>{ATTACK_LABELS[result.dominant_attack] ?? result.dominant_attack}</strong>
          {' · '}Effective dimension: <strong>{result.effective_n}</strong>
        </p>
      </div>

      {/* Attack table */}
      <div>
        <h3 className="text-sm font-semibold text-slate-700 mb-2">Attack Cost Breakdown</h3>
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-4 py-2">Attack</th>
                <th className="text-right px-4 py-2">log₂(cost)</th>
                <th className="text-right px-4 py-2">β (BKZ block)</th>
                <th className="text-right px-4 py-2">d (dimension)</th>
              </tr>
            </thead>
            <tbody>
              {attacks.map(([name, cost]) => (
                <tr
                  key={name}
                  className={`border-t border-slate-100 ${name === result.dominant_attack ? 'bg-indigo-50 font-semibold' : ''}`}
                >
                  <td className="px-4 py-2">
                    {ATTACK_LABELS[name] ?? name}
                    {name === result.dominant_attack && (
                      <span className="ml-2 text-xs bg-indigo-200 text-indigo-700 px-1.5 py-0.5 rounded">dominant</span>
                    )}
                  </td>
                  <td className="text-right px-4 py-2 font-mono">
                    {cost.error ? <span className="text-red-500 text-xs">{cost.error}</span>
                      : cost.rop_log2 != null ? `≈ 2^${cost.rop_log2}` : '—'}
                  </td>
                  <td className="text-right px-4 py-2 font-mono">{cost.beta ?? '—'}</td>
                  <td className="text-right px-4 py-2 font-mono">{cost.d ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bar chart of attack costs */}
      {chartData.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-2">Attack Cost Comparison</h3>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis
                  domain={['auto', 'auto']}
                  tickFormatter={v => `2^${v}`}
                  tick={{ fontSize: 11 }}
                  width={52}
                />
                <Tooltip formatter={(v) => [`≈ 2^${v}`, 'log₂(cost)']} />
                <Line
                  type="monotone"
                  dataKey="log₂(cost)"
                  stroke={COLORS[0]}
                  strokeWidth={2}
                  dot={{ r: 5, fill: COLORS[0] }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Warnings */}
      {result.warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-xs font-semibold text-yellow-700 mb-1">Modelling notes</p>
          <ul className="space-y-1">
            {result.warnings.map((w, idx) => (
              <li key={idx} className="text-xs text-yellow-700">• {w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
