"use client"

import { useEffect, useState } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { useToast } from "@/components/ui/use-toast"

interface AdminAuthProps {
  onChange?: () => void
}

export function AdminAuth({ onChange }: AdminAuthProps) {
  const [token, setToken] = useState("")
  const { toast } = useToast()

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("admin_token") || ""
      setToken(saved)
    }
  }, [])

  const save = () => {
    localStorage.setItem("admin_token", token.trim())
    toast({ title: "Admin token saved" })
    onChange?.()
  }

  const clear = () => {
    localStorage.removeItem("admin_token")
    setToken("")
    toast({ title: "Admin token cleared" })
    onChange?.()
  }

  return (
    <div className="flex items-end gap-3">
      <div className="flex-1">
        <Label htmlFor="admin-token">Admin Token</Label>
        <Input
          id="admin-token"
          type="password"
          placeholder="Enter admin token"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
      </div>
      <Button onClick={save}>Save</Button>
      <Button variant="outline" onClick={clear}>Clear</Button>
    </div>
  )
}