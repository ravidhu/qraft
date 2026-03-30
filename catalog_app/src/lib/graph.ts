import type { Node, Edge } from "@xyflow/react"
import type { Manifest } from "@/types/manifest"

export interface ModelNodeData {
  label: string
  materialization: string
  description: string
  tags: string[]
  isSource: boolean
  [key: string]: unknown
}

export function buildGraph(manifest: Manifest): {
  nodes: Node<ModelNodeData>[]
  edges: Edge[]
} {
  const nodes: Node<ModelNodeData>[] = []
  const edges: Edge[] = []
  const addedNodes = new Set<string>()

  // Add source nodes
  for (const [srcName, srcConfig] of Object.entries(manifest.sources)) {
    for (const table of srcConfig.tables) {
      const id = `source:${srcName}.${table}`
      if (!addedNodes.has(id)) {
        addedNodes.add(id)
        nodes.push({
          id,
          type: "model",
          position: { x: 0, y: 0 },
          data: {
            label: `${srcName}.${table}`,
            materialization: "source",
            description: "",
            tags: [],
            isSource: true,
          },
        })
      }
    }
  }

  // Add model nodes
  for (const [name, node] of Object.entries(manifest.nodes)) {
    if (!addedNodes.has(name)) {
      addedNodes.add(name)
      nodes.push({
        id: name,
        type: "model",
        position: { x: 0, y: 0 },
        data: {
          label: name,
          materialization: node.materialization,
          description: node.description,
          tags: node.tags,
          isSource: false,
        },
      })
    }
  }

  // Add edges from parent_map
  for (const [child, parents] of Object.entries(manifest.parent_map)) {
    for (const parent of parents) {
      // Edge color matches the source node (color flows outward)
      const sourceMat = parent.startsWith("source:")
        ? "source"
        : (manifest.nodes[parent]?.materialization ?? "view")
      edges.push({
        id: `${parent}->${child}`,
        source: parent,
        target: child,
        type: "animated",
        data: { materialization: sourceMat },
      })
    }
  }

  return { nodes, edges }
}
