"use client"

import { useState, useCallback } from 'react'
import { SearchBar } from '@/components/search-bar'
import { ResultCard } from '@/components/result-card'
import { LowConfidenceBanner } from '@/components/low-confidence-banner'
import { Badge } from '@/components/ui/badge'
import { searchOccupations } from '@/lib/api'
import type { SearchResponse } from '@/lib/types'

export default function HomePage() {
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [currentQuery, setCurrentQuery] = useState('')

  const handleSearch = useCallback(async (query: string, k: number) => {
    setIsSearching(true)
    setCurrentQuery(query)
    
    try {
      const response = await searchOccupations(query, k)
      setSearchResponse(response)
    } catch (error) {
      console.error('Search failed:', error)
      setSearchResponse(null)
    } finally {
      setIsSearching(false)
    }
  }, [])

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-3xl font-bold">Find Your Occupation</h2>
        <p className="text-muted-foreground">
          Search in English, Hindi, Bengali, or Marathi
        </p>
      </div>

      <SearchBar onSearch={handleSearch} isSearching={isSearching} />

      {searchResponse && (
        <div className="space-y-4">
          {searchResponse.low_confidence && <LowConfidenceBanner />}
          
          {searchResponse.language !== 'en' && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Detected language:</span>
              <Badge variant="secondary">{searchResponse.language.toUpperCase()}</Badge>
              {searchResponse.translated && (
                <Badge variant="outline">Translated</Badge>
              )}
            </div>
          )}

          <div className="space-y-3">
            {searchResponse.results.map((result) => (
              <ResultCard
                key={result.nco_code}
                result={result}
                query={currentQuery}
              />
            ))}
          </div>

          {searchResponse.results.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              No results found. Try different keywords.
            </div>
          )}
        </div>
      )}
    </div>
  )
}