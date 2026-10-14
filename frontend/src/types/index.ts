export type Scheme = 'LWE' | 'RLWE' | 'MLWE'
export type FindParam = 'n' | 'q' | 'sigma' | 'k'

export type SecretDistribution =
  | 'binary'
  | 'ternary'
  | 'gaussian'
  | 'uniform'
  | 'centred_binomial'

export interface EstimateRequest {
  scheme: Scheme
  n: number
  q: number
  sigma?: number
  alpha?: number
  m?: number
  k?: number
  eta?: number
  secret_distribution: SecretDistribution
}

export interface AttackCost {
  rop_log2: number | null
  beta?: number
  d?: number
  tag?: string
  error?: string
}

export interface EstimateResponse {
  lambda_bits: number
  dominant_attack: string
  attacks: Record<string, AttackCost>
  effective_n: number
  parameters_used: Record<string, unknown>
  warnings: string[]
}

export interface Preset {
  name: string
  scheme: Scheme
  n: number
  q: number
  sigma?: number
  eta?: number
  k?: number
  secret_distribution: SecretDistribution
  reference: string
}

export interface KnownParams {
  n?: number
  q?: number
  sigma?: number
  alpha?: number
  eta?: number
  k?: number
  m?: number
  secret_distribution: SecretDistribution
}

export interface FindParamRequest {
  scheme: Scheme
  target_lambda: number
  find_param: FindParam
  known: KnownParams
}

export interface Verification {
  at_found: number | null
  at_step_below: number | null
  step_below_label: string
}

export interface FindParamResponse {
  found_param: string
  found_value: number
  verification: Verification
  parameters_complete: Record<string, unknown>
  warnings: string[]
}
