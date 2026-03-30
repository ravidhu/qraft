import type { Manifest } from "@/types/manifest"
import { Badge } from "@/components/ui/badge"

interface DependenciesTabProps {
  modelName: string
  manifest: Manifest
  onSelectModel: (name: string) => void
}

export function DependenciesTab({ modelName, manifest, onSelectModel }: DependenciesTabProps) {
  const parents = manifest.parent_map[modelName] ?? []
  const children = manifest.child_map[modelName] ?? []

  return (
    <div className="flex gap-8 px-4 py-3">
      <div className="flex-1">
        <h4 className="text-xs font-semibold text-muted-foreground mb-2 uppercase">Upstream ({parents.length})</h4>
        {parents.length === 0 ? (
          <div className="text-xs text-muted-foreground">No upstream dependencies</div>
        ) : (
          <div className="flex flex-col gap-1">
            {parents.map((p) => {
              const isSource = p.startsWith("source:")
              return (
                <button
                  key={p}
                  className="flex items-center gap-2 text-xs text-left hover:bg-accent rounded px-2 py-1"
                  onClick={() => !isSource && onSelectModel(p)}
                  disabled={isSource}
                >
                  <Badge variant="outline" className="text-[10px] px-1 h-4">
                    {isSource ? "source" : manifest.nodes[p]?.materialization ?? "?"}
                  </Badge>
                  <span className="font-mono">{p}</span>
                </button>
              )
            })}
          </div>
        )}
      </div>
      <div className="flex-1">
        <h4 className="text-xs font-semibold text-muted-foreground mb-2 uppercase">Downstream ({children.length})</h4>
        {children.length === 0 ? (
          <div className="text-xs text-muted-foreground">No downstream dependents</div>
        ) : (
          <div className="flex flex-col gap-1">
            {children.map((c) => (
              <button
                key={c}
                className="flex items-center gap-2 text-xs text-left hover:bg-accent rounded px-2 py-1"
                onClick={() => onSelectModel(c)}
              >
                <Badge variant="outline" className="text-[10px] px-1 h-4">
                  {manifest.nodes[c]?.materialization ?? "?"}
                </Badge>
                <span className="font-mono">{c}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
