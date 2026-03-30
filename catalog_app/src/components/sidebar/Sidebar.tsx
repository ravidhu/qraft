import { useState } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import type { Manifest } from "@/types/manifest"
import { SearchInput } from "./SearchInput"
import { ModelTree } from "./ModelTree"

interface SidebarProps {
  manifest: Manifest
  open: boolean
  selectedModel: string | null
  onSelectModel: (name: string) => void
}

export function Sidebar({ manifest, open, selectedModel, onSelectModel }: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState("")

  const modelCount = Object.keys(manifest.nodes).length
  const sourceCount = Object.keys(manifest.sources).length

  return (
    <div
      className={`h-full bg-sidebar border-r border-sidebar-border flex flex-col transition-[width] duration-200 ${
        open ? "w-[260px]" : "w-0"
      } overflow-hidden`}
    >
      <div className="px-3 py-3 shrink-0">
        <div className="text-xs text-muted-foreground">
          {modelCount} models &middot; {sourceCount} sources
        </div>
      </div>
      <SearchInput value={searchQuery} onChange={setSearchQuery} />
      <Separator />
      <ScrollArea className="flex-1">
        <ModelTree
          manifest={manifest}
          searchQuery={searchQuery}
          selectedModel={selectedModel}
          onSelectModel={onSelectModel}
        />
      </ScrollArea>
    </div>
  )
}
