"use client"

import { useState, useEffect, useCallback } from 'react'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { MicButton } from './mic-button'

interface SearchBarProps {
  onSearch: (query: string, k: number) => void
  isSearching?: boolean
}

export function SearchBar({ onSearch, isSearching }: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [k, setK] = useState('5')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, 400)

    return () => clearTimeout(timer)
  }, [query])

  // Trigger search on debounced query change
  useEffect(() => {
    if (debouncedQuery.trim()) {
      onSearch(debouncedQuery, parseInt(k))
    }
  }, [debouncedQuery, k, onSearch])

  const handleMicTranscript = useCallback((transcript: string) => {
    setQuery(transcript)
  }, [])

  return (
    <div className="w-full max-w-2xl mx-auto space-y-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
        <Input
          type="text"
          placeholder="Search for occupations in English, Hindi, Bengali, or Marathi..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10 pr-12"
          disabled={isSearching}
        />
        <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
          <MicButton onTranscript={handleMicTranscript} />
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        <Label htmlFor="results-count">Results:</Label>
        <Select value={k} onValueChange={setK}>
          <SelectTrigger id="results-count" className="w-20">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {[3, 5, 7, 10].map((num) => (
              <SelectItem key={num} value={num.toString()}>
                {num}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}