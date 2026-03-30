import { useState, useEffect } from "react"
import type { TestResults } from "@/types/manifest"

export function useTestResults() {
  const [testResults, setTestResults] = useState<TestResults | null>(null)

  useEffect(() => {
    fetch("./test_results.json")
      .then((res) => {
        if (!res.ok) return null
        return res.json()
      })
      .then((data: TestResults | null) => {
        if (data) setTestResults(data)
      })
      .catch(() => {
        // test_results.json is optional
      })
  }, [])

  return { testResults }
}
