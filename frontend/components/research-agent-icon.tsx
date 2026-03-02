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
            aria-label="Deep Research Agent"
            className="relative h-9 w-9 gap-1.5 rounded-full bg-primary/10 px-0 transition-colors hover:bg-primary/20 md:w-auto md:px-3"
            onClick={onClick}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 text-primary animate-spin" />
            ) : (
              <Search className="w-4 h-4 text-primary" />
            )}
            <span aria-hidden className="hidden text-sm font-medium text-primary md:inline">Research</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>Deep Research Agent</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
