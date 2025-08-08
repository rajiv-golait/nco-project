"use client"

import { useState } from 'react'
import { ThumbsUp, ThumbsDown } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/components/ui/use-toast'
import { submitFeedback } from '@/lib/api'

interface FeedbackDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  query: string
  selectedCode?: string
}

export function FeedbackDialog({ open, onOpenChange, query, selectedCode }: FeedbackDialogProps) {
  const [helpful, setHelpful] = useState<boolean | null>(null)
  const [comments, setComments] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { toast } = useToast()

  const handleSubmit = async () => {
    if (helpful === null) return

    setIsSubmitting(true)
    try {
      await submitFeedback({
        query,
        selected_code: selectedCode,
        results_helpful: helpful,
        comments: comments.trim() || undefined,
      })
      
      toast({
        title: "Thank you for your feedback!",
        description: "Your input helps us improve search results.",
      })
      
      onOpenChange(false)
      // Reset state
      setHelpful(null)
      setComments('')
    } catch (error) {
      toast({
        title: "Error submitting feedback",
        description: "Please try again later.",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Was this result helpful?</DialogTitle>
          <DialogDescription>
            Your feedback helps us improve search results for everyone.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="flex justify-center gap-4">
            <Button
              variant={helpful === true ? "default" : "outline"}
              size="lg"
              onClick={() => setHelpful(true)}
              className="flex-1"
            >
              <ThumbsUp className="h-4 w-4 mr-2" />
              Yes
            </Button>
            <Button
              variant={helpful === false ? "default" : "outline"}
              size="lg"
              onClick={() => setHelpful(false)}
              className="flex-1"
            >
              <ThumbsDown className="h-4 w-4 mr-2" />
              No
            </Button>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="comments">Additional comments (optional)</Label>
            <Textarea
              id="comments"
              placeholder="Tell us more about your experience..."
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              rows={3}
            />
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={helpful === null || isSubmitting}
          >
            Submit Feedback
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}