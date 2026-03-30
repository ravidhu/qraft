import { useState, useEffect } from "react"
import type { Manifest } from "@/types/manifest"

export function useManifest() {
  const [manifest, setManifest] = useState<Manifest | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch("./manifest.json")
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load manifest.json (${res.status})`)
        return res.json()
      })
      .then((data: Manifest) => {
        setManifest(data)
        setLoading(false)
      })
      .catch((err: Error) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  return { manifest, error, loading }
}
