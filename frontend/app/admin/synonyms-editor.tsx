"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useToast } from '@/components/ui/use-toast'
import { RefreshCw, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getAdminHeaders } from '@/lib/admin'

interface SynonymsEditorProps {
  onUpdate: () => void
}

export function SynonymsEditor({ onUpdate }: SynonymsEditorProps) {
  const [ncoCode, setNcoCode] = useState('')
  const [addSynonyms, setAddSynonyms] = useState('')
  const [removeSynonyms, setRemoveSynonyms] = useState('')
  const [isUpdating, setIsUpdating] = useState(false)
  const [isReindexing, setIsReindexing] = useState(false)
  const [requiresReindex, setRequiresReindex] = useState(false)
  const { toast } = useToast()

  const handleUpdateSynonyms = async () => {
    if (!ncoCode.trim()) {
      toast({
        title: "NCO code required",
        description: "Please enter an NCO code",
        variant: "destructive"
      })
      return
    }

    setIsUpdating(true)
    try {
      const updates = [{
        nco_code: ncoCode.trim(),
        add: addSynonyms.split(',').map(s => s.trim()).filter(Boolean),
        remove: removeSynonyms.split(',').map(s => s.trim()).filter(Boolean)
      }]

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/update-synonyms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAdminHeaders() },
        body: JSON.stringify({ updates })
      })

      if (!response.ok) throw new Error('Update failed')
      
      const result = await response.json()
      
      if (result.invalid_codes?.length > 0) {
        toast({
          title: "Invalid NCO code",
          description: `Code ${result.invalid_codes[0]} not found`,
          variant: "destructive"
        })
      } else {
        toast({
          title: "Synonyms updated",
          description: `Updated ${result.updated} occupation(s)`,
        })
        setNcoCode('')
        setAddSynonyms('')
        setRemoveSynonyms('')
        setRequiresReindex(result.requires_reindex)
      }
    } catch (error) {
      toast({
        title: "Update failed",
        description: "Failed to update synonyms",
        variant: "destructive"
      })
    } finally {
      setIsUpdating(false)
    }
  }

  const handleReindex = async () => {
    setIsReindexing(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/reindex`, {
        method: 'POST',
        headers: { ...getAdminHeaders() }
      })

      if (!response.ok) throw new Error('Reindex failed')
      
      const result = await response.json()
      
      toast({
        title: "Reindex complete",
        description: `Indexed ${result.vectors} occupations in ${result.duration_ms}ms`,
      })
      
      setRequiresReindex(false)
      onUpdate() // Refresh stats
    } catch (error) {
      toast({
        title: "Reindex failed",
        description: "Failed to rebuild search index",
        variant: "destructive"
      })
    } finally {
      setIsReindexing(false)
    }
  }

  return (
    <div className="space-y-6">
      {requiresReindex && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Synonyms have been updated. Reindex to apply changes to search.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4">
        <div>
          <Label htmlFor="nco-code">NCO Code</Label>
          <Input
            id="nco-code"
            placeholder="e.g., 7212.0100"
            value={ncoCode}
            onChange={(e) => setNcoCode(e.target.value)}
          />
        </div>

        <div>
          <Label htmlFor="add-synonyms">Add Synonyms (comma-separated)</Label>
          <Textarea
            id="add-synonyms"
            placeholder="e.g., new synonym 1, new synonym 2"
            value={addSynonyms}
            onChange={(e) => setAddSynonyms(e.target.value)}
            rows={3}
          />
        </div>

        <div>
          <Label htmlFor="remove-synonyms">Remove Synonyms (comma-separated)</Label>
          <Textarea
            id="remove-synonyms"
            placeholder="e.g., old synonym 1, old synonym 2"
            value={removeSynonyms}
            onChange={(e) => setRemoveSynonyms(e.target.value)}
            rows={3}
          />
        </div>

        <div className="flex gap-2">
          <Button
            onClick={handleUpdateSynonyms}
            disabled={isUpdating || isReindexing}
          >
            Update Synonyms
          </Button>

          <Button
            onClick={handleReindex}
            disabled={isReindexing}
            variant={requiresReindex ? "default" : "outline"}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", isReindexing && "animate-spin")} />
            Reindex
          </Button>
        </div>
      </div>
    </div>
  )
}