export interface ManifestMetadata {
  project_name: string
  env: string
  schema: string
  connection_type: string
  generated_at: string
}

export interface ManifestNode {
  name: string
  path: string
  raw_sql: string
  compiled_sql: string
  ddl: string
  target: string
  materialization: string
  refs: string[]
  sources: [string, string][]
  description: string
  tags: string[]
  enabled: boolean
}

export interface ManifestSource {
  schema: string
  database: string | null
  tables: string[]
}

export interface Manifest {
  metadata: ManifestMetadata
  nodes: Record<string, ManifestNode>
  sources: Record<string, ManifestSource>
  parent_map: Record<string, string[]>
  child_map: Record<string, string[]>
  batches: string[][]
}

export interface TestResultEntry {
  model: string
  column: string
  test_type: string
  severity: string
  passed: boolean
  params?: Record<string, unknown>
  where?: string
  failures_count?: number
  failures_sample?: string[][]
  error?: string
}

export interface TestResultsSummary {
  total: number
  passed: number
  failed: number
  warned: number
  errored: number
}

export interface TestResults {
  metadata: {
    env: string
    schema: string
    generated_at: string
  }
  summary: TestResultsSummary
  results: TestResultEntry[]
}
