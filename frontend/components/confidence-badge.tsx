import { cn } from '@/lib/utils'

interface ConfidenceBadgeProps {
  confidence: number
  className?: string
}

export function ConfidenceBadge({ confidence, className }: ConfidenceBadgeProps) {
  const percentage = Math.round(confidence * 100)
  
  const getColorClass = () => {
    if (percentage >= 70) return 'bg-green-100 text-green-800'
    if (percentage >= 40) return 'bg-yellow-100 text-yellow-800'
    return 'bg-red-100 text-red-800'
  }

  return (
    <span className={cn(
      "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium",
      getColorClass(),
      className
    )}>
      {percentage}% match
    </span>
  )
}