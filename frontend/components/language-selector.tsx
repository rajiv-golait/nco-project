"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface LanguageSelectorProps {
  value: string | null
  onChange: (language: string | null) => void
}

const LANGUAGES = [
  { code: 'en', label: 'EN', name: 'English' },
  { code: 'hi', label: 'HI', name: 'हिन्दी' },
  { code: 'bn', label: 'BN', name: 'বাংলা' },
  { code: 'mr', label: 'MR', name: 'मराठी' },
]

export function LanguageSelector({ value, onChange }: LanguageSelectorProps) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    // Load persisted language preference
    const saved = localStorage.getItem('preferred_language')
    if (saved && LANGUAGES.some(l => l.code === saved)) {
      onChange(saved)
    }
  }, [onChange])

  const handleSelect = (code: string | null) => {
    onChange(code)
    if (code) {
      localStorage.setItem('preferred_language', code)
    } else {
      localStorage.removeItem('preferred_language')
    }
  }

  if (!mounted) return null

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground">Language:</span>
      <div className="flex gap-1">
        <Button
          size="sm"
          variant={value === null ? "default" : "outline"}
          onClick={() => handleSelect(null)}
          className="h-7 px-2 text-xs"
        >
          Auto
        </Button>
        {LANGUAGES.map((lang) => (
          <Button
            key={lang.code}
            size="sm"
            variant={value === lang.code ? "default" : "outline"}
            onClick={() => handleSelect(lang.code)}
            className="h-7 px-2 text-xs"
            title={lang.name}
          >
            {lang.label}
          </Button>
        ))}
      </div>
    </div>
  )
}