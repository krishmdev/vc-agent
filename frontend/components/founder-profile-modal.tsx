"use client"

import { useState } from "react"
import { User, X, Edit3, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"

interface FounderProfileModalProps {
  isOpen: boolean
  onClose: () => void
}

export function FounderProfileModal({ isOpen, onClose }: FounderProfileModalProps) {
  const { founder, setFounder } = useAppStore()
  const [isEditing, setIsEditing] = useState(false)
  const [localFounder, setLocalFounder] = useState(founder)

  const handleSave = () => {
    setFounder(localFounder)
    setIsEditing(false)
  }

  const handleCancel = () => {
    setLocalFounder(founder)
    setIsEditing(false)
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 z-50 bg-foreground/20 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="fixed left-4 top-20 z-50 w-96 animate-in slide-in-from-left-2 fade-in duration-300">
        <div className="bg-card border border-border rounded-2xl shadow-xl overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-border bg-secondary/30">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <User className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Founder Profile</h3>
                <p className="text-xs text-muted-foreground">Your journey details</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full hover:bg-secondary flex items-center justify-center transition-colors"
            >
              <X className="w-4 h-4 text-muted-foreground" />
            </button>
          </div>

          {/* Content */}
          <div className="p-4 space-y-4">
            {isEditing ? (
              <>
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-sm font-medium">Name</Label>
                  <Input
                    id="name"
                    value={localFounder.name}
                    onChange={(e) => setLocalFounder({ ...localFounder, name: e.target.value })}
                    placeholder="Your name"
                    className="bg-background"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-sm font-medium">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={localFounder.email}
                    onChange={(e) => setLocalFounder({ ...localFounder, email: e.target.value })}
                    placeholder="you@example.com"
                    className="bg-background"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="motivation" className="text-sm font-medium">
                    <span className="flex items-center gap-2">
                      <Sparkles className="w-3.5 h-3.5 text-primary" />
                      Why are you building this?
                    </span>
                  </Label>
                  <Textarea
                    id="motivation"
                    value={localFounder.motivation}
                    onChange={(e) => setLocalFounder({ ...localFounder, motivation: e.target.value })}
                    placeholder="What drives you to build this product?"
                    className="bg-background min-h-24 resize-none"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="background" className="text-sm font-medium">Background</Label>
                  <Textarea
                    id="background"
                    value={localFounder.background}
                    onChange={(e) => setLocalFounder({ ...localFounder, background: e.target.value })}
                    placeholder="Your relevant experience and skills"
                    className="bg-background min-h-20 resize-none"
                  />
                </div>
                <div className="flex gap-2 pt-2">
                  <Button variant="outline" onClick={handleCancel} className="flex-1 bg-transparent">
                    Cancel
                  </Button>
                  <Button onClick={handleSave} className="flex-1">
                    Save Profile
                  </Button>
                </div>
              </>
            ) : (
              <>
                {/* Motivation Section - Primary */}
                <div className="p-4 rounded-xl bg-primary/5 border border-primary/10">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium text-foreground">Founder Motivation</span>
                  </div>
                  {founder.motivation ? (
                    <p className="text-sm text-foreground leading-relaxed">{founder.motivation}</p>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">
                      Share why you are building this product...
                    </p>
                  )}
                </div>

                {/* Details */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between py-2 border-b border-border/50">
                    <span className="text-sm text-muted-foreground">Name</span>
                    <span className="text-sm font-medium text-foreground">
                      {founder.name || "Not set"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border/50">
                    <span className="text-sm text-muted-foreground">Email</span>
                    <span className="text-sm font-medium text-foreground">
                      {founder.email || "Not set"}
                    </span>
                  </div>
                  {founder.background && (
                    <div className="pt-2">
                      <span className="text-sm text-muted-foreground">Background</span>
                      <p className="text-sm text-foreground mt-1">{founder.background}</p>
                    </div>
                  )}
                </div>

                <Button 
                  variant="outline" 
                  onClick={() => setIsEditing(true)} 
                  className="w-full bg-transparent gap-2"
                >
                  <Edit3 className="w-4 h-4" />
                  Edit Profile
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
