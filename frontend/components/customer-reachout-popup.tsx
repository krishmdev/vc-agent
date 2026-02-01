"use client"

import * as React from "react"
import { Users } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

interface CustomerReachoutPopupProps {
  isOpen: boolean
  onClose: () => void
  onFindCustomers: (icp: string, type: "B2C" | "B2B") => void
  anchorRef?: React.RefObject<HTMLElement | null>
}

export function CustomerReachoutPopup({ 
  isOpen, 
  onClose, 
  onFindCustomers,
  anchorRef 
}: CustomerReachoutPopupProps) {
  const [icpDescription, setIcpDescription] = React.useState("")
  const [customerType, setCustomerType] = React.useState<"B2C" | "B2B">("B2C")

  // Handle clicking outside to close
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
        if (!isOpen) return
        
        const target = event.target as Node
        const popup = document.getElementById("customer-reachout-popup")
        
        // If click is outside popup and not on the anchor element (the tab button)
        if (popup && !popup.contains(target) && anchorRef?.current && !anchorRef.current.contains(target)) {
            onClose()
        }
    }

    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [isOpen, onClose, anchorRef])

  if (!isOpen) return null

  return (
    <div 
      id="customer-reachout-popup"
      className="absolute top-full left-0 z-50 w-[400px] mt-2 animate-in fade-in zoom-in-95 duration-200"
    >
      <div className="bg-popover border border-border rounded-xl shadow-xl overflow-hidden p-4 space-y-4">
        
        <div className="space-y-1.5">
          <h3 className="font-medium text-sm text-foreground">
            Write a one-line description of your ideal customer profile.
          </h3>
        </div>

        <Textarea
          value={icpDescription}
          onChange={(e) => setIcpDescription(e.target.value)}
          placeholder="e.g., Small business owners who manage their own social media"
          className="min-h-[80px] resize-none bg-background text-sm"
        />

        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-muted-foreground">Customer type</span>
          
          <div className="flex bg-secondary/50 p-1 rounded-lg">
            <button
              onClick={() => setCustomerType("B2C")}
              className={cn(
                "px-3 py-1 text-xs font-medium rounded-md transition-all",
                customerType === "B2C" 
                  ? "bg-background text-foreground shadow-sm" 
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              B2C
            </button>
            <button
              onClick={() => setCustomerType("B2B")}
              className={cn(
                "px-3 py-1 text-xs font-medium rounded-md transition-all",
                customerType === "B2B" 
                  ? "bg-background text-foreground shadow-sm" 
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              B2B
            </button>
          </div>
        </div>

        <Button
          onClick={() => onFindCustomers(icpDescription, customerType)}
          disabled={!icpDescription.trim()}
          className="w-full"
        >
            <Users className="w-4 h-4 mr-2" />
            Find customers!
        </Button>

      </div>
    </div>
  )
}
