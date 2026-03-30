import {
  BaseEdge,
  getSmoothStepPath,
  getBezierPath,
  getStraightPath,
  type EdgeProps,
} from "@xyflow/react"

export type EdgeLineType = "smoothstep" | "bezier" | "straight"

const DOT_COLORS: Record<string, string> = {
  view: "#3b82f6",
  table: "#22c55e",
  table_incremental: "#f97316",
  ephemeral: "#9ca3af",
  materialized_view: "#a855f7",
  source: "#d97706",
}

const EDGE_COLORS: Record<string, string> = {
  view: "#93c5fd",
  table: "#86efac",
  table_incremental: "#fdba74",
  ephemeral: "#d1d5db",
  materialized_view: "#d8b4fe",
  source: "#fcd34d",
}

export function AnimatedEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style,
}: EdgeProps) {
  const materialization = (data?.materialization as string) ?? "view"
  const lineType = (data?.lineType as EdgeLineType) ?? "smoothstep"
  const dotColor = DOT_COLORS[materialization] ?? "#6b7280"
  const edgeColor = EDGE_COLORS[materialization] ?? "#d1d5db"
  const isEphemeral = materialization === "ephemeral"

  const pathParams = { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition }

  let edgePath: string
  if (lineType === "bezier") {
    ;[edgePath] = getBezierPath(pathParams)
  } else if (lineType === "straight") {
    ;[edgePath] = getStraightPath(pathParams)
  } else {
    ;[edgePath] = getSmoothStepPath({ ...pathParams, borderRadius: 16 })
  }

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          stroke: edgeColor,
          strokeWidth: 2,
          strokeDasharray: isEphemeral ? "6 4" : undefined,
        }}
      />
      <circle r={3.5} fill={dotColor}>
        <animateMotion dur="2.5s" repeatCount="indefinite" path={edgePath} />
      </circle>
    </>
  )
}
