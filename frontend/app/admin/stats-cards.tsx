import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Search, AlertCircle, ThumbsUp, Zap } from 'lucide-react'

interface StatsCardsProps {
  stats: any
  isLoading: boolean
}

export function StatsCards({ stats, isLoading }: StatsCardsProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                <Skeleton className="h-4 w-24" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const cards = [
    {
      title: "Searches (24h)",
      value: stats?.last_24h?.total_searches || 0,
      icon: Search,
      color: "text-blue-600"
    },
    {
      title: "Low Confidence Rate",
      value: `${Math.round((stats?.last_24h?.low_confidence_rate || 0) * 100)}%`,
      icon: AlertCircle,
      color: "text-yellow-600"
    },
    {
      title: "Helpful Feedback",
      value: `${Math.round((stats?.all_time?.feedback_helpful_rate || 0) * 100)}%`,
      icon: ThumbsUp,
      color: "text-green-600"
    },
    {
      title: "Avg Latency",
      value: `${Math.round(stats?.all_time?.avg_latency_ms || 0)}ms`,
      icon: Zap,
      color: "text-purple-600"
    }
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
            <card.icon className={`h-4 w-4 ${card.color}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{card.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}