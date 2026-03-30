import type { TestResultEntry } from "@/types/manifest"
import { Badge } from "@/components/ui/badge"

interface ColumnsTabProps {
  modelName: string
  testResults: TestResultEntry[]
}

export function ColumnsTab({ modelName, testResults }: ColumnsTabProps) {
  // Group tests by column
  const testsByColumn = new Map<string, TestResultEntry[]>()
  for (const t of testResults) {
    if (t.model === modelName) {
      const existing = testsByColumn.get(t.column) ?? []
      existing.push(t)
      testsByColumn.set(t.column, existing)
    }
  }

  if (testsByColumn.size === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4">
        No column tests found. Define tests in model front-matter and run <code className="bg-muted px-1 rounded">qraft test</code>.
      </div>
    )
  }

  return (
    <div className="overflow-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left px-4 py-2 font-medium">Column</th>
            <th className="text-left px-4 py-2 font-medium">Test</th>
            <th className="text-left px-4 py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {Array.from(testsByColumn.entries()).map(([column, tests]) =>
            tests.map((test, i) => (
              <tr key={`${column}-${test.test_type}-${i}`} className="border-b last:border-0">
                <td className="px-4 py-1.5 font-mono text-xs">{i === 0 ? column : ""}</td>
                <td className="px-4 py-1.5">{test.test_type}</td>
                <td className="px-4 py-1.5">
                  {test.error ? (
                    <Badge variant="destructive" className="text-[10px]">ERROR</Badge>
                  ) : test.passed ? (
                    <Badge className="bg-green-100 text-green-800 text-[10px]">PASS</Badge>
                  ) : test.severity === "warn" ? (
                    <Badge className="bg-yellow-100 text-yellow-800 text-[10px]">WARN</Badge>
                  ) : (
                    <Badge variant="destructive" className="text-[10px]">FAIL</Badge>
                  )}
                </td>
              </tr>
            )),
          )}
        </tbody>
      </table>
    </div>
  )
}
