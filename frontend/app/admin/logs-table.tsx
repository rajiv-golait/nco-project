"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Download } from 'lucide-react'
import { useToast } from '@/components/ui/use-toast'

export function LogsTable() {
  const [logs, setLogs] = useState<any[]>([])
  const [logType, setLogType] = useState<'search' | 'feedback'>('search')
  const [limit, setLimit] = useState('100')
  const [isLoading, setIsLoading] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    fetchLogs()
  }, [logType, limit])

  const fetchLogs = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/admin/logs?type=${logType}&limit=${limit}&fields=basic`
      )
      if (!response.ok) throw new Error('Failed to fetch logs')
      const data = await response.json()
      setLogs(data)
    } catch (error) {
      toast({
        title: "Error loading logs",
        description: "Failed to fetch log data",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const exportCSV = () => {
    const headers = logType === 'search' 
      ? ['Timestamp', 'Query', 'Language', 'Top Code', 'Score', 'Low Confidence']
      : ['Timestamp', 'Query', 'Selected Code', 'Helpful', 'Comments']
    
    const rows = logs.map(log => {
      if (logType === 'search') {
        return [
          log.timestamp,
          log.query,
          log.language,
          log.top_nco_code || '',
          log.top_score || '',
          log.low_confidence
        ]
      } else {
        return [
          log.timestamp,
          log.query,
          log.selected_code || '',
          log.results_helpful,
          log.comments || ''
        ]
      }
    })
    
    const csv = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n')
    
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${logType}-logs-${new Date().toISOString()}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Tabs value={logType} onValueChange={(v) => setLogType(v as any)}>
          <TabsList>
            <TabsTrigger value="search">Search Logs</TabsTrigger>
            <TabsTrigger value="feedback">Feedback Logs</TabsTrigger>
          </TabsList>
        </Tabs>
        
        <div className="flex items-center gap-2">
          <Select value={limit} onValueChange={setLimit}>
            <SelectTrigger className="w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="50">50</SelectItem>
              <SelectItem value="100">100</SelectItem>
              <SelectItem value="500">500</SelectItem>
            </SelectContent>
          </Select>
          
          <Button
            size="sm"
            variant="outline"
            onClick={exportCSV}
            disabled={logs.length === 0}
          >
            <Download className="h-4 w-4 mr-1" />
            Export
          </Button>
        </div>
      </div>

      <div className="rounded-md border">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                {logType === 'search' ? (
                  <>
                    <th className="text-left p-2">Time</th>
                    <th className="text-left p-2">Query</th>
                    <th className="text-left p-2">Lang</th>
                    <th className="text-left p-2">Top Result</th>
                    <th className="text-left p-2">Score</th>
                    <th className="text-left p-2">Status</th>
                  </>
                ) : (
                  <>
                    <th className="text-left p-2">Time</th>
                    <th className="text-left p-2">Query</th>
                    <th className="text-left p-2">Selected</th>
                    <th className="text-left p-2">Helpful</th>
                    <th className="text-left p-2">Comments</th>
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
                        <td className="p-2 font-mono text-xs">{log.selected_code || '-'}</td>
                        <td className="p-2">
                          <Badge variant={log.results_helpful ? "default" : "secondary"}>
                            {log.results_helpful ? "Yes" : "No"}
                          </Badge>
                        </td>
                        <td className="p-2 text-xs max-w-xs truncate">{log.comments || '-'}</td>
                      </>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}