"use client"

import { useState } from 'react'
import Link from 'next/link'
import { Star, StarOff, MessageSquare } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ConfidenceBadge } from './confidence-badge'
import { FeedbackDialog } from './feedback-dialog'
import type { SearchResult } from '@/lib/types'

interface ResultCardProps {
  result: SearchResult
  query: string
}

function highlightMatch(text: string, matches: string[]): React.ReactNode {
  if (!matches.length) return text
  
  // Create a regex pattern from matches
  const pattern = matches
    .map(m => m.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')
  const regex = new RegExp(`(${pattern})`, 'gi')
  
  const parts = text.split(regex)
  
  return parts.map((part, i) => {
    if (matches.some(m => m.toLowerCase() === part.toLowerCase())) {
      return <mark key={i} className="bg-yellow-200 px-0.5">{part}</mark>
    }
    return part
  })
}

export function ResultCard({ result, query }: ResultCardProps) {
  const [isFavorite, setIsFavorite] = useState(() => {
    if (typeof window === 'undefined') return false
    const favorites = JSON.parse(localStorage.getItem('favorites') || '[]')
    return favorites.includes(result.nco_code)
  })
  const [showFeedback, setShowFeedback] = useState(false)

  const toggleFavorite = () => {
    const newFavorite = !isFavorite
    setIsFavorite(newFavorite)
    
    const favorites = JSON.parse(localStorage.getItem('favorites') || '[]')
    if (newFavorite) {
      favorites.push(result.nco_code)
    } else {
      const index = favorites.indexOf(result.nco_code)
      if (index > -1) favorites.splice(index, 1)
    }
    localStorage.setItem('favorites', JSON.stringify(favorites))
  }

  return (
    <>
      <Card className="hover:shadow-lg transition-shadow">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <Link href={`/occupation/${result.nco_code}`} className="flex-1">
              <CardTitle className="text-lg hover:text-primary transition-colors">
                {highlightMatch(result.title, result.matched_synonyms)}
              </CardTitle>
            </Link>
            <div className="flex items-center gap-2">
              <ConfidenceBadge confidence={result.confidence} />
              <Button
                size="icon"
                variant="ghost"
                onClick={toggleFavorite}
                className="h-8 w-8"
                aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
              >
                {isFavorite ? (
                  <Star className="h-4 w-4 fill-current" />
                ) : (
                  <StarOff className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
          <CardDescription className="text-xs text-muted-foreground">
            NCO Code: {result.nco_code}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground line-clamp-2">
            {result.description}
          </p>
          
          {result.matched_synonyms.length > 0 && (
            <div className="flex flex-wrap gap-1">
              <span className="text-xs text-muted-foreground">Matched:</span>
              {result.matched_synonyms.map((synonym, index) => (
                <Badge key={index} variant="secondary" className="text-xs">
                  {synonym}
                </Badge>
              ))}
            </div>
          )}
          
          <div className="flex justify-end">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowFeedback(true)}
              className="text-xs"
            >
              <MessageSquare className="h-3 w-3 mr-1" />
              Helpful?
            </Button>
          </div>
        </CardContent>
      </Card>
      
      <FeedbackDialog
        open={showFeedback}
        onOpenChange={setShowFeedback}
        query={query}
        selectedCode={result.nco_code}
      />
    </>
  )
}