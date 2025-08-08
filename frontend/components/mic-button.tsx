"use client"

import { useState, useEffect } from 'react'
import { Mic, MicOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface MicButtonProps {
  onTranscript: (transcript: string) => void
}

export function MicButton({ onTranscript }: MicButtonProps) {
  const [isListening, setIsListening] = useState(false)
  const [isSupported, setIsSupported] = useState(false)

  useEffect(() => {
    // Check if Web Speech API is supported
    if (typeof window !== 'undefined') {
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition
      if (SpeechRecognition) {
        setIsSupported(true)
      }
    }
  }, [])

  const startListening = () => {
    if (!isSupported) return

    const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition
    const recognition = new SpeechRecognition()
    
    // Try Hindi first, fallback to English (India)
    try {
      recognition.lang = 'hi-IN'
    } catch {
      recognition.lang = 'en-IN'
    }
    
    recognition.continuous = false
    recognition.interimResults = false

    recognition.onstart = () => {
      setIsListening(true)
    }

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript
      onTranscript(transcript)
      setIsListening(false)
    }

    recognition.onerror = () => {
      setIsListening(false)
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    try {
      recognition.start()
    } catch (error) {
      console.error('Speech recognition error:', error)
      setIsListening(false)
    }
  }

  if (!isSupported) {
    return null
  }

  return (
    <Button
      type="button"
      size="icon"
      variant="ghost"
      onClick={startListening}
      disabled={isListening}
      className={cn(
        "h-8 w-8",
        isListening && "text-red-500"
      )}
      aria-label={isListening ? "Listening..." : "Voice search (Hindi)"}
      title={isListening ? "Listening..." : "Voice search (Hindi)"}
    >
      {isListening ? (
        <MicOff className="h-4 w-4" />
      ) : (
        <Mic className="h-4 w-4" />
      )}
    </Button>
  )
}