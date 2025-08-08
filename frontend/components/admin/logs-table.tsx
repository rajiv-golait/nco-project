"use client"

import { useState, useEffect } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { getAdminLogs } from "@/lib/api"

interface Log {
  timestamp: string
  query: string
  language: string
  low_confidence: boolean
  top_nco_code?: string
  top_score?: number
  results_helpful?: boolean
  comments?: string
}

export function LogsTable() {
  const [logs, setLogs] = useState<Log[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [logType, setLogType] = useState<'search' | 'feedback'>('search')
  const [limit, setLimit] = useState(100)

  useEffect(() => {
    fetchLogs()
  }, [logType, limit])

  const fetchLogs = async () => {
    try {
      const data = await getAdminLogs(logType, limit, 'basic')
      setLogs(data)
    } catch (error) {
      console.error('Failed to fetch logs:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const exportCSV = () => {
    const headers = logType === 'search' 
      ? ['Timestamp', 'Query', 'Language', 'Low Confidence', 'Top NCO Code', 'Top Score']
      : ['Timestamp', 'Query', 'Helpful', 'Comments']
    
    const csvContent = [
      headers.join(','),
      ...logs.map(log => {
        if (logType === 'search') {
          return [
            log.timestamp,
            `"${log.query}"`,
            log.language,
            log.low_confidence ? 'Yes' : 'No',
            log.top_nco_code || '',
            log.top_score?.toFixed(2) || ''
          ].join(',')
        } else {
          return [
            log.timestamp,
            `"${log.query}"`,
            log.results_helpful ? 'Yes' : 'No',
            `"${log.comments || ''}"`
          ].join(',')
        }
      })
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${logType}_logs.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <Tabs value={logType} onValueChange={(value) => setLogType(value as 'search' | 'feedback')}>
          <TabsList>
            <TabsTrigger value="search">Search Logs</TabsTrigger>
            <TabsTrigger value="feedback">Feedback Logs</TabsTrigger>
          </TabsList>
        </Tabs>
        
        <div className="flex gap-2">
          <select 
            value={limit} 
            onChange={(e) => setLimit(Number(e.target.value))}
            className="border rounded px-2 py-1"
          >
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={500}>500</option>
            <option value={1000}>1000</option>
          </select>
          <Button onClick={exportCSV} size="sm">Export CSV</Button>
        </div>
      </div>

      <div className="border rounded-lg">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              {logType === 'search' ? (
                <>
                  <th className="p-2 text-left text-xs font-medium">Timestamp</th>
                  <th className="p-2 text-left text-xs font-medium">Query</th>
                  <th className="p-2 text-left text-xs font-medium">Language</th>
                  <th className="p-2 text-left text-xs font-medium">Top Code</th>
                  <th className="p-2 text-left text-xs font-medium">Score</th>
                  <th className="p-2 text-left text-xs font-medium">Confidence</th>
                </>
              ) : (
                <>
                  <th className="p-2 text-left text-xs font-medium">Timestamp</th>
                  <th className="p-2 text-left text-xs font-medium">Query</th>
                  <th className="p-2 text-left text-xs font-medium">Helpful</th>
                  <th className="p-2 text-left text-xs font-medium">Comments</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} className="text-center p-4 text-muted-foreground">
                  Loading...
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center p-4 text-muted-foreground">
                  No logs found
                </td>
              </tr>
            ) : (
              logs.map((log, i) => (
                <tr key={i} className="border-b">
                  {logType === 'search' ? (
                    <>
                      <td className="p-2 text-xs text-muted-foreground">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="p-2">{log.query}</td>
                      <td className="p-2">
                        <Badge variant="outline" className="text-xs">
                          {log.language}
                        </Badge>
                      </td>
                      <td className="p-2 font-mono text-xs">{log.top_nco_code || '-'}</td>
                      <td className="p-2">{log.top_score?.toFixed(2) || '-'}</td>
                      <td className="p-2">
                        {log.low_confidence && (
                          <Badge variant="secondary" className="text-xs">
                            Low Conf
                          </Badge>
                        )}
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="p-2 text-xs text-muted-foreground">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="p-2">{log.query}</td>
                      <td className="p-2">
                        <Badge variant={log.results_helpful ? "default" : "destructive"} className="text-xs">
                          {log.results_helpful ? 'Yes' : 'No'}
                        </Badge>
                      </td>
                      <td className="p-2 text-sm">{log.comments || '-'}</td>
                    </>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
