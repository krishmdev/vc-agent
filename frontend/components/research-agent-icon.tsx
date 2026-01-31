"use client"

import { Search, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface ResearchAgentIconProps {
  onClick: () => void
  isLoading?: boolean
}

export function ResearchAgentIcon({ onClick, isLoading = false }: ResearchAgentIconProps) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="relative w-9 h-9 rounded-full bg-primary/10 hover:bg-primary/20 transition-colors"
            onClick={onClick}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 text-primary animate-spin" />
            ) : (
              <Search className="w-4 h-4 text-primary" />
            )}
            <span className="sr-only">Deep Research Agent</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>Deep Research Agent</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
