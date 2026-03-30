import { useState, useMemo } from "react"
import { ChevronRight, FileCode, Folder } from "lucide-react"
import type { Manifest } from "@/types/manifest"

interface TreeNode {
  name: string
  fullPath: string
  isModel: boolean
  children: TreeNode[]
}

function buildTree(manifest: Manifest): TreeNode {
  const root: TreeNode = { name: "models", fullPath: "models", isModel: false, children: [] }

  for (const [name, node] of Object.entries(manifest.nodes)) {
    // path is like "models/staging/stg_customers.sql"
    const parts = node.path.replace(/\.sql$/, "").split("/")
    // Skip the "models" prefix if present
    const segments = parts[0] === "models" ? parts.slice(1) : parts

    let current = root
    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i]
      const isLast = i === segments.length - 1

      if (isLast) {
        current.children.push({
          name: segment,
          fullPath: name,
          isModel: true,
          children: [],
        })
      } else {
        let folder = current.children.find((c) => !c.isModel && c.name === segment)
        if (!folder) {
          folder = { name: segment, fullPath: "", isModel: false, children: [] }
          current.children.push(folder)
        }
        current = folder
      }
    }
  }

  // Sort: folders first, then models, both alphabetically
  function sortTree(node: TreeNode) {
    node.children.sort((a, b) => {
      if (a.isModel !== b.isModel) return a.isModel ? 1 : -1
      return a.name.localeCompare(b.name)
    })
    node.children.forEach(sortTree)
  }
  sortTree(root)

  return root
}

function filterTree(node: TreeNode, query: string): TreeNode | null {
  if (!query) return node
  const lower = query.toLowerCase()

  if (node.isModel) {
    return node.name.toLowerCase().includes(lower) ? node : null
  }

  const filteredChildren = node.children
    .map((c) => filterTree(c, query))
    .filter((c): c is TreeNode => c !== null)

  if (filteredChildren.length === 0) return null
  return { ...node, children: filteredChildren }
}

interface ModelTreeProps {
  manifest: Manifest
  searchQuery: string
  selectedModel: string | null
  onSelectModel: (name: string) => void
}

export function ModelTree({ manifest, searchQuery, selectedModel, onSelectModel }: ModelTreeProps) {
  const tree = useMemo(() => buildTree(manifest), [manifest])
  const filteredTree = useMemo(() => filterTree(tree, searchQuery), [tree, searchQuery])

  if (!filteredTree || filteredTree.children.length === 0) {
    return <div className="px-3 py-2 text-sm text-muted-foreground">No models found</div>
  }

  return (
    <div className="px-1 py-1">
      {filteredTree.children.map((child) => (
        <TreeNodeItem
          key={child.isModel ? child.fullPath : child.name}
          node={child}
          depth={0}
          selectedModel={selectedModel}
          onSelectModel={onSelectModel}
          defaultOpen={!!searchQuery}
        />
      ))}
    </div>
  )
}

interface TreeNodeItemProps {
  node: TreeNode
  depth: number
  selectedModel: string | null
  onSelectModel: (name: string) => void
  defaultOpen: boolean
}

function TreeNodeItem({ node, depth, selectedModel, onSelectModel, defaultOpen }: TreeNodeItemProps) {
  const [open, setOpen] = useState(defaultOpen)

  if (node.isModel) {
    const isSelected = node.fullPath === selectedModel
    return (
      <button
        className={`flex items-center gap-1.5 w-full text-left px-2 py-1 text-sm rounded-md transition-colors ${
          isSelected ? "bg-primary text-primary-foreground" : "hover:bg-accent"
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => onSelectModel(node.fullPath)}
      >
        <FileCode className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{node.name}</span>
      </button>
    )
  }

  return (
    <div>
      <button
        className="flex items-center gap-1.5 w-full text-left px-2 py-1 text-sm rounded-md hover:bg-accent font-medium"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => setOpen(!open)}
      >
        <ChevronRight className={`h-3.5 w-3.5 shrink-0 transition-transform ${open ? "rotate-90" : ""}`} />
        <Folder className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{node.name}</span>
      </button>
      {open && (
        <div>
          {node.children.map((child) => (
            <TreeNodeItem
              key={child.isModel ? child.fullPath : child.name}
              node={child}
              depth={depth + 1}
              selectedModel={selectedModel}
              onSelectModel={onSelectModel}
              defaultOpen={defaultOpen}
            />
          ))}
        </div>
      )}
    </div>
  )
}
