"use client"

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { StatsCards } from '@/components/admin/stats-cards'
import { LogsTable } from '@/components/admin/logs-table'
import { SynonymsEditor } from '@/components/admin/synonyms-editor'
import { useToast } from '@/components/ui/use-toast'
import { AdminAuth } from '@/components/admin/admin-auth'
import { getAdminStats } from '@/lib/api'

export default function AdminPage() {
  const [stats, setStats] = useState<any>(null)
  const [isLoadingStats, setIsLoadingStats] = useState(true)
  const { toast } = useToast()

  const fetchStats = useCallback(async () => {
    try {
      const data = await getAdminStats()
      setStats(data)
    } catch (error) {
      toast({
        title: "Error loading stats",
        description: "Failed to fetch statistics",
        variant: "destructive"
      })
    } finally {
      setIsLoadingStats(false)
    }
  }, [toast])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h2 className="text-3xl font-bold">Admin Dashboard</h2>
          <p className="text-muted-foreground">Monitor and manage the NCO search system</p>
        </div>
        <AdminAuth onChange={fetchStats} />
      </div>

      <StatsCards stats={stats} isLoading={isLoadingStats} />

      <Tabs defaultValue="logs" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="synonyms">Synonyms</TabsTrigger>
          <TabsTrigger value="stats">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="logs">
          <Card>
            <CardHeader>
              <CardTitle>System Logs</CardTitle>
              <CardDescription>View search and feedback logs</CardDescription>
            </CardHeader>
            <CardContent>
              <LogsTable />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="synonyms">
          <Card>
            <CardHeader>
              <CardTitle>Synonym Management</CardTitle>
              <CardDescription>Update occupation synonyms and rebuild search index</CardDescription>
            </CardHeader>
            <CardContent>
              <SynonymsEditor onUpdate={fetchStats} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="stats">
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Top Queries</CardTitle>
              </CardHeader>
              <CardContent>
                {stats?.all_time?.top_queries && (
                  <div className="space-y-2">
                    {stats.all_time.top_queries.map(([query, count]: [string, number], i: number) => (
                      <div key={i} className="flex justify-between items-center">
                        <span className="text-sm">{query}</span>
                        <span className="text-sm text-muted-foreground">{count} searches</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Top Occupations</CardTitle>
              </CardHeader>
              <CardContent>
                {stats?.all_time?.top_codes && (
                  <div className="space-y-2">
                    {stats.all_time.top_codes.map(([code, count]: [string, number], i: number) => (
                      <div key={i} className="flex justify-between items-center">
                        <span className="text-sm font-mono">{code}</span>
                        <span className="text-sm text-muted-foreground">{count} times</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}