import { X, GripHorizontal } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import type { Manifest, TestResultEntry } from "@/types/manifest"
import { ColumnsTab } from "./ColumnsTab"
import { SqlTab } from "./SqlTab"
import { DependenciesTab } from "./DependenciesTab"

interface DetailPanelProps {
  modelName: string
  manifest: Manifest
  testResults: TestResultEntry[]
  onClose: () => void
  onSelectModel: (name: string) => void
}

export function DetailPanel({ modelName, manifest, testResults, onClose, onSelectModel }: DetailPanelProps) {
  const node = manifest.nodes[modelName]
  if (!node) return null

  const modelTests = testResults.filter((t) => t.model === modelName)
  const passedTests = modelTests.filter((t) => t.passed).length
  const totalTests = modelTests.length

  return (
    <div className="h-full flex flex-col bg-background border-t">
      {/* Drag handle */}
      <div className="flex justify-center py-1 cursor-grab">
        <GripHorizontal className="h-4 w-4 text-muted-foreground" />
      </div>

      {/* Header */}
      <div className="flex items-center justify-between px-4 pb-2 shrink-0">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-sm">{node.name}</h3>
          <Badge variant="outline" className="text-xs">
            {node.materialization}
          </Badge>
          {node.tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="text-[10px]">
              {tag}
            </Badge>
          ))}
          <span className="text-xs text-muted-foreground font-mono">{node.target}</span>
          {totalTests > 0 && (
            <span className="text-xs text-muted-foreground">
              Tests: {passedTests}/{totalTests} passed
            </span>
          )}
        </div>
        <button onClick={onClose} className="p-1 hover:bg-accent rounded">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Description */}
      {node.description && (
        <div className="px-4 pb-2 text-sm text-muted-foreground shrink-0">{node.description}</div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="sql" className="flex-1 flex flex-col min-h-0">
        <TabsList className="mx-4 shrink-0 w-fit">
          <TabsTrigger value="sql">SQL</TabsTrigger>
          <TabsTrigger value="dependencies">Dependencies</TabsTrigger>
          <TabsTrigger value="columns">
            Columns & Tests
            {totalTests > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-[10px] px-1 h-4">
                {totalTests}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>
        <TabsContent value="sql" className="flex-1 min-h-0 overflow-auto mt-0">
          <SqlTab node={node} />
        </TabsContent>
        <TabsContent value="dependencies" className="flex-1 min-h-0 overflow-auto mt-0">
          <DependenciesTab modelName={modelName} manifest={manifest} onSelectModel={onSelectModel} />
        </TabsContent>
        <TabsContent value="columns" className="flex-1 min-h-0 overflow-auto mt-0">
          <ColumnsTab modelName={modelName} testResults={testResults} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
