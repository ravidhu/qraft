import { memo } from "react"
import { Handle, Position, type NodeProps } from "@xyflow/react"
import type { ModelNodeData } from "@/lib/graph"
import { Badge } from "@/components/ui/badge"

const MATERIALIZATION_COLORS: Record<string, string> = {
  view: "bg-blue-100 text-blue-800 border-blue-300",
  table: "bg-green-100 text-green-800 border-green-300",
  table_incremental: "bg-orange-100 text-orange-800 border-orange-300",
  ephemeral: "bg-gray-100 text-gray-500 border-dashed border-gray-300",
  materialized_view: "bg-purple-100 text-purple-800 border-purple-300",
  source: "bg-amber-100 text-amber-800 border-amber-300",
}

function ModelNodeComponent({ data, selected }: NodeProps) {
  const nodeData = data as ModelNodeData
  const colorClass = MATERIALIZATION_COLORS[nodeData.materialization] ?? "bg-gray-100 text-gray-800 border-gray-300"
  const isSource = nodeData.isSource

  return (
    <div
      className={`px-3 py-2 rounded-lg border-2 shadow-sm min-w-[160px] max-w-[220px] cursor-pointer transition-shadow ${
        selected ? "shadow-md ring-2 ring-primary" : "hover:shadow-md"
      } ${isSource ? "border-dashed" : ""} ${colorClass}`}
    >
      <Handle type="target" position={Position.Left} className="!w-2 !h-2" />
      <div className="flex flex-col gap-1">
        <div className="font-medium text-xs truncate">{nodeData.label}</div>
        <div className="flex items-center gap-1">
          <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">
            {nodeData.materialization}
          </Badge>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!w-2 !h-2" />
    </div>
  )
}

export const ModelNode = memo(ModelNodeComponent)
