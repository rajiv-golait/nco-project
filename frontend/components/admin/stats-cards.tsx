"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface StatsCardsProps {
  stats: {
    last_24h: {
      total_searches: number
      low_confidence_rate: number
    }
    all_time: {
      total_searches: number
      low_confidence_rate: number
      avg_latency_ms: number
      feedback_helpful_rate: number
    }
  }
  isLoading?: boolean
}

export function StatsCards({ stats, isLoading }: StatsCardsProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Loading...</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">-</div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  // Handle case where stats is null or missing required fields
  if (!stats || !stats.last_24h || !stats.all_time) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">No Data</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-muted-foreground">-</div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Searches (24h)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.last_24h.total_searches || 0}</div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Low Confidence Rate</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {((stats.last_24h.low_confidence_rate || 0) * 100).toFixed(1)}%
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Avg Latency</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{(stats.all_time.avg_latency_ms || 0).toFixed(0)}ms</div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Feedback Helpful</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {((stats.all_time.feedback_helpful_rate || 0) * 100).toFixed(1)}%
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
