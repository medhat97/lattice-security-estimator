import { useEffect, useState } from 'react'
import SchemeSelector from './components/SchemeSelector'
import ParameterForm from './components/ParameterForm'
import ResultsPanel from './components/ResultsPanel'
import ParameterFinder from './components/ParameterFinder'
import { getPresets, postEstimate } from './api/estimator'
import { parseApiError } from './api/parseError'
import type { EstimateRequest, EstimateResponse, Preset, Scheme } from './types'

type Tool = 'estimate' | 'find'

export default function App() {
  const [activeTool, setActiveTool] = useState<Tool>('estimate')

  // Security Estimation state
  const [scheme, setScheme]     = useState<Scheme>('LWE')
  const [presets, setPresets]   = useState<Preset[]>([])
  const [result, setResult]     = useState<EstimateResponse | null>(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)

  useEffect(() => {
    getPresets().then(setPresets).catch(() => {})
  }, [])

  const handleSchemeChange = (s: Scheme) => {
    setScheme(s)
    setResult(null)
    setError(null)
  }

  const handleEstimate = async (req: EstimateRequest) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await postEstimate(req))
    } catch (e: unknown) {
      setError(parseApiError(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">

      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-800">Lattice Security Estimator</h1>
            <p className="text-xs text-slate-500">LWE · RLWE · MLWE parameter analysis</p>
          </div>

          {/* Tool tabs */}
          <nav className="flex bg-slate-100 rounded-lg p-1 gap-1">
            <button
              onClick={() => setActiveTool('estimate')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTool === 'estimate'
                  ? 'bg-white text-indigo-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Security Estimation
            </button>
            <button
              onClick={() => setActiveTool('find')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTool === 'find'
                  ? 'bg-white text-violet-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Parameter Estimation
            </button>
          </nav>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">

        {/* ── Tool 1: Security Estimation ── */}
        {activeTool === 'estimate' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <h2 className="text-base font-semibold text-slate-700 mb-4">Parameters</h2>
              <SchemeSelector value={scheme} onChange={handleSchemeChange} />
              <ParameterForm
                scheme={scheme}
                presets={presets}
                onSubmit={handleEstimate}
                loading={loading}
              />
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <h2 className="text-base font-semibold text-slate-700 mb-4">Results</h2>

              {!result && !loading && !error && (
                <div className="flex flex-col items-center justify-center h-64 text-slate-400 text-sm">
                  <svg className="w-12 h-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 11h.01M12 11h.01M15 11h.01M4 19h16a2 2 0 002-2V7a2 2 0 00-2-2H4a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  Enter parameters and press Estimate Security
                </div>
              )}

              {loading && (
                <div className="flex flex-col items-center justify-center h-64 text-slate-500 text-sm">
                  <div className="w-8 h-8 border-4 border-indigo-300 border-t-indigo-600 rounded-full animate-spin mb-4" />
                  Running…
                </div>
              )}

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
                  <strong>Error:</strong> {error}
                </div>
              )}

              {result && <ResultsPanel result={result} />}
            </div>
          </div>
        )}

        {/* ── Tool 2: Parameter Estimation ── */}
        {activeTool === 'find' && <ParameterFinder />}

        <p className="text-center text-xs text-slate-400 mt-8">
          Based on{' '}
          <a href="https://github.com/malb/lattice-estimator" target="_blank"
            rel="noreferrer" className="underline">
            Albrecht et al. lattice-estimator
          </a>
          {' '}· estimates depend on the chosen cost model and estimator assumptions.
        </p>
      </main>
    </div>
  )
}
