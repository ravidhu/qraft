import { useState } from "react"
import type { ManifestNode } from "@/types/manifest"

interface SqlTabProps {
  node: ManifestNode
}

export function SqlTab({ node }: SqlTabProps) {
  const [showCompiled, setShowCompiled] = useState(true)
  const sql = showCompiled ? node.compiled_sql : node.raw_sql

  return (
    <div className="flex flex-col h-full">
      <div className="flex gap-2 px-4 py-2 shrink-0">
        <button
          className={`text-xs px-2 py-1 rounded ${showCompiled ? "bg-primary text-primary-foreground" : "bg-muted"}`}
          onClick={() => setShowCompiled(true)}
        >
          Compiled SQL
        </button>
        <button
          className={`text-xs px-2 py-1 rounded ${!showCompiled ? "bg-primary text-primary-foreground" : "bg-muted"}`}
          onClick={() => setShowCompiled(false)}
        >
          Raw SQL
        </button>
      </div>
      <div className="flex-1 overflow-auto px-4 pb-4">
        <pre className="bg-muted rounded-md p-3 text-xs font-mono whitespace-pre-wrap break-words">
          {sql || "No SQL available"}
        </pre>
      </div>
    </div>
  )
}
