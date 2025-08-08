"use client"

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Star, StarOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { getOccupation } from '@/lib/api'
import type { OccupationDetail } from '@/lib/types'

export default function OccupationPage() {
  const params = useParams()
  const router = useRouter()
  const ncoCode = params.nco_code as string
  
  const [occupation, setOccupation] = useState<OccupationDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isFavorite, setIsFavorite] = useState(false)

  useEffect(() => {
    async function fetchOccupation() {
      try {
        const data = await getOccupation(ncoCode)
        setOccupation(data)
        
        // Check if favorite
        const favorites = JSON.parse(localStorage.getItem('favorites') || '[]')
        setIsFavorite(favorites.includes(ncoCode))
      } catch (err) {
        setError('Failed to load occupation details')
      } finally {
        setIsLoading(false)
      }
    }

    fetchOccupation()
  }, [ncoCode])

  const toggleFavorite = () => {
    const newFavorite = !isFavorite
    setIsFavorite(newFavorite)
    
    const favorites = JSON.parse(localStorage.getItem('favorites') || '[]')
    if (newFavorite) {
      favorites.push(ncoCode)
    } else {
      const index = favorites.indexOf(ncoCode)
      if (index > -1) favorites.splice(index, 1)
    }
    localStorage.setItem('favorites', JSON.stringify(favorites))
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    )
  }

  if (error || !occupation) {
    return (
      <div className="text-center space-y-4">
        <p className="text-destructive">{error || 'Occupation not found'}</p>
        <Button onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Go Back
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Search
        </Button>
        
        <Button
          size="icon"
          variant="ghost"
          onClick={toggleFavorite}
          aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
        >
          {isFavorite ? (
            <Star className="h-5 w-5 fill-current" />
          ) : (
            <StarOff className="h-5 w-5" />
          )}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">{occupation.title}</CardTitle>
          <CardDescription>NCO Code: {occupation.nco_code}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <h3 className="font-semibold mb-2">Description</h3>
            <p className="text-muted-foreground">{occupation.description}</p>
          </div>

          {occupation.synonyms.length > 0 && (
            <div>
              <h3 className="font-semibold mb-2">Also Known As</h3>
              <div className="flex flex-wrap gap-2">
                {occupation.synonyms.map((synonym, index) => (
                  <Badge key={index} variant="secondary">
                    {synonym}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {occupation.examples.length > 0 && (
            <div>
              <h3 className="font-semibold mb-2">Common Examples</h3>
              <ul className="list-disc list-inside space-y-1">
                {occupation.examples.map((example, index) => (
                  <li key={index} className="text-muted-foreground">
                    {example}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}