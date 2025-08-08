import { AlertCircle } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

export function LowConfidenceBanner() {
  return (
    <Alert className="mb-4">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Low confidence results</AlertTitle>
      <AlertDescription>
        The results below may not be accurate. Try refining your search with more specific terms or different keywords.
      </AlertDescription>
    </Alert>
  )
}