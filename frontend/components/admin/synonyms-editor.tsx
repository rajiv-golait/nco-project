"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/components/ui/use-toast"
import { getAdminHeaders } from "@/lib/auth"

interface SynonymsEditorProps {
  onUpdate?: () => void
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
        onUpdate?.()
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
        headers: getAdminHeaders()
      })

      if (!response.ok) throw new Error('Reindex failed')
      
      const result = await response.json()
      
      toast({
        title: "Reindex complete",
        description: `Indexed ${result.vectors} vectors in ${result.duration_ms}ms`,
      })
      setRequiresReindex(false)
      onUpdate?.()
    } catch (error) {
      toast({
        title: "Reindex failed",
        description: "Failed to rebuild index",
        variant: "destructive"
      })
    } finally {
      setIsReindexing(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4">
        <div>
          <Label htmlFor="nco-code">NCO Code</Label>
          <Input
            id="nco-code"
            value={ncoCode}
            onChange={(e) => setNcoCode(e.target.value)}
            placeholder="e.g., 7212.0100"
          />
        </div>
        
        <div>
          <Label htmlFor="add-synonyms">Add Synonyms (comma-separated)</Label>
          <Input
            id="add-synonyms"
            value={addSynonyms}
            onChange={(e) => setAddSynonyms(e.target.value)}
            placeholder="e.g., arc welder, TIG welder"
          />
        </div>
        
        <div>
          <Label htmlFor="remove-synonyms">Remove Synonyms (comma-separated)</Label>
          <Input
            id="remove-synonyms"
            value={removeSynonyms}
            onChange={(e) => setRemoveSynonyms(e.target.value)}
            placeholder="e.g., old term, outdated term"
          />
        </div>
      </div>

      <div className="flex gap-2">
        <Button 
          onClick={handleUpdateSynonyms} 
          disabled={isUpdating || !ncoCode.trim()}
        >
          {isUpdating ? 'Updating...' : 'Update Synonyms'}
        </Button>
        
        {requiresReindex && (
          <Button 
            onClick={handleReindex} 
            disabled={isReindexing}
            variant="secondary"
          >
            {isReindexing ? 'Reindexing...' : 'Reindex'}
          </Button>
        )}
      </div>
    </div>
  )
}
