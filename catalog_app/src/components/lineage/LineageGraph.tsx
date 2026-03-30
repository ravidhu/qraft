import { useCallback, useEffect, useMemo } from "react"
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type NodeMouseHandler,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

import type { Manifest } from "@/types/manifest"
import { buildGraph } from "@/lib/graph"
import { applyDagreLayout } from "./layout"
import { ModelNode } from "./ModelNode"
import { AnimatedEdge, type EdgeLineType } from "./AnimatedEdge"

const nodeTypes = { model: ModelNode }
const edgeTypes = { animated: AnimatedEdge }

interface LineageGraphProps {
  manifest: Manifest
  selectedModel: string | null
  onSelectModel: (name: string | null) => void
  edgeLineType: EdgeLineType
}

export function LineageGraph({ manifest, selectedModel, onSelectModel, edgeLineType }: LineageGraphProps) {
  const { layoutNodes, graphEdges } = useMemo(() => {
    const { nodes: rawNodes, edges } = buildGraph(manifest)
    const laid = applyDagreLayout(rawNodes, edges)
    return { layoutNodes: laid, graphEdges: edges }
  }, [manifest])

  const nodesWithSelection = useMemo(
    () => layoutNodes.map((n) => ({ ...n, selected: n.id === selectedModel })),
    [layoutNodes, selectedModel],
  )

  const edgesWithLineType = useMemo(
    () => graphEdges.map((e) => ({ ...e, data: { ...e.data, lineType: edgeLineType } })),
    [graphEdges, edgeLineType],
  )

  const [nodes, setNodes, onNodesChange] = useNodesState(nodesWithSelection)
  const [edges, setEdges, onEdgesChange] = useEdgesState(edgesWithLineType)

  useEffect(() => {
    setNodes(nodesWithSelection)
  }, [nodesWithSelection, setNodes])

  useEffect(() => {
    setEdges(edgesWithLineType)
  }, [edgesWithLineType, setEdges])

  const onNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      if (node.id.startsWith("source:")) return
      onSelectModel(node.id === selectedModel ? null : node.id)
    },
    [onSelectModel, selectedModel],
  )

  const onPaneClick = useCallback(() => {
    onSelectModel(null)
  }, [onSelectModel])

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={onNodeClick}
      onPaneClick={onPaneClick}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.1}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
    >
      <Background />
      <Controls />
      <MiniMap
        nodeColor={(node) => {
          const mat = (node.data as Record<string, unknown>)?.materialization as string
          switch (mat) {
            case "view": return "#dbeafe"
            case "table": return "#dcfce7"
            case "table_incremental": return "#fed7aa"
            case "ephemeral": return "#f3f4f6"
            case "source": return "#fef3c7"
            default: return "#e5e7eb"
          }
        }}
        zoomable
        pannable
      />
    </ReactFlow>
  )
}
