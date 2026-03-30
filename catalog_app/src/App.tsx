import { useState, useCallback } from "react"
import { Menu, Spline, GitCommitHorizontal, Minus } from "lucide-react"
import { useManifest } from "@/hooks/use-manifest"
import { useTestResults } from "@/hooks/use-test-results"
import { Sidebar } from "@/components/sidebar/Sidebar"
import { LineageGraph } from "@/components/lineage/LineageGraph"
import { DetailPanel } from "@/components/detail-panel/DetailPanel"
import type { EdgeLineType } from "@/components/lineage/AnimatedEdge"

const EDGE_OPTIONS: { value: EdgeLineType; label: string; icon: typeof Spline }[] = [
  { value: "smoothstep", label: "Smooth Step", icon: GitCommitHorizontal },
  { value: "bezier", label: "Bezier", icon: Spline },
  { value: "straight", label: "Straight", icon: Minus },
]

export default function App() {
  const { manifest, error, loading } = useManifest()
  const { testResults } = useTestResults()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [edgeLineType, setEdgeLineType] = useState<EdgeLineType>("smoothstep")

  const handleSelectModel = useCallback((name: string | null) => {
    setSelectedModel(name)
  }, [])

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-muted-foreground">Loading catalog...</div>
      </div>
    )
  }

  if (error || !manifest) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-lg font-semibold text-destructive mb-2">Failed to load catalog</h2>
          <p className="text-sm text-muted-foreground">{error ?? "manifest.json not found"}</p>
          <p className="text-sm text-muted-foreground mt-2">
            Run <code className="bg-muted px-1.5 py-0.5 rounded">qraft docs generate --env &lt;env&gt;</code> first.
          </p>
        </div>
      </div>
    )
  }

  const panelOpen = selectedModel !== null

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Header */}
      <header className="h-10 border-b flex items-center justify-between px-3 shrink-0 bg-background z-10">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 hover:bg-accent rounded-md"
            title={sidebarOpen ? "Close sidebar" : "Open sidebar"}
          >
            <Menu className="h-4 w-4" />
          </button>
          <span className="font-semibold text-sm">Qraft Catalog</span>
        </div>
        <div className="flex items-center gap-3">
          {/* Edge line type switcher */}
          <div className="flex items-center border rounded-md overflow-hidden">
            {EDGE_OPTIONS.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                onClick={() => setEdgeLineType(value)}
                className={`p-1.5 transition-colors ${
                  edgeLineType === value
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-accent text-muted-foreground"
                }`}
                title={label}
              >
                <Icon className="h-3.5 w-3.5" />
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>{manifest.metadata.project_name}</span>
            <span className="text-border">|</span>
            <span>{manifest.metadata.env}</span>
            <span className="text-border">|</span>
            <span>{manifest.metadata.connection_type}</span>
          </div>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 min-h-0">
        {/* Sidebar */}
        <Sidebar
          manifest={manifest}
          open={sidebarOpen}
          selectedModel={selectedModel}
          onSelectModel={(name) => handleSelectModel(name)}
        />

        {/* Main content */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Lineage graph */}
          <div className={`flex-1 min-h-0 ${panelOpen ? "h-[60%]" : "h-full"}`}>
            <LineageGraph
              manifest={manifest}
              selectedModel={selectedModel}
              onSelectModel={handleSelectModel}
              edgeLineType={edgeLineType}
            />
          </div>

          {/* Detail panel */}
          {panelOpen && selectedModel && (
            <div className="h-[40%] min-h-[200px] overflow-hidden">
              <DetailPanel
                modelName={selectedModel}
                manifest={manifest}
                testResults={testResults?.results ?? []}
                onClose={() => handleSelectModel(null)}
                onSelectModel={handleSelectModel}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
