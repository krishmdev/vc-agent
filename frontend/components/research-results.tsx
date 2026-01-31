"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, AlertTriangle, CheckCircle2, XCircle, TrendingUp, Search } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface ResearchResultsProps {
  isOpen: boolean
  onClose: () => void
  status: "idle" | "loading" | "complete" | "error"
  data: any // using any for now, will type strictly later
  error?: string
}

export function ResearchResults({ isOpen, onClose, status, data, error }: ResearchResultsProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-y-0 right-0 w-full md:w-[600px] z-50 bg-background border-l border-border shadow-2xl flex flex-col transition-transform duration-300 ease-in-out transform translate-x-0">
      <div className="h-16 border-b border-border flex items-center justify-between px-6 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center gap-2">
           <div className="p-1.5 rounded-md bg-primary/10">
             <Search className="w-4 h-4 text-primary" />
           </div>
           <h2 className="font-semibold text-lg">Deep Research Analysis</h2>
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          ✕
        </button>
      </div>

      <ScrollArea className="flex-1 p-6">
        {status === "loading" && (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
             <Loader2 className="w-8 h-8 text-primary animate-spin" />
             <div className="text-center space-y-1">
               <p className="font-medium">Conducting Deep Research...</p>
               <p className="text-sm text-muted-foreground">Analyzing market trends, failure modes, and customer signals.</p>
               <p className="text-xs text-muted-foreground/60 max-w-xs mx-auto">This may take several minutes as the agent browses live sources.</p>
             </div>
          </div>
        )}

        {status === "error" && (
          <div className="flex flex-col items-center justify-center py-20 text-center space-y-2">
            <AlertTriangle className="w-8 h-8 text-destructive" />
            <p className="font-medium text-destructive">Research Failed</p>
            <p className="text-sm text-muted-foreground">{error || "An unknown error occurred."}</p>
          </div>
        )}

        {status === "complete" && data && (
          <div className="space-y-8 animate-in fade-in duration-500">
            {/* Fallback for raw output if JSON parsing failed but we have text */}
            {(!data.timing_verdict && data.raw_output) && (
              <div className="space-y-4">
                 <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-500">
                    <p className="font-medium text-sm flex items-center gap-2">
                       <AlertTriangle className="w-4 h-4" />
                       Analysis Format Issue
                    </p>
                    <p className="text-xs opacity-90 mt-1">
                      The research agent produced a response but it wasn't in the expected structured format. The raw analysis is shown below.
                    </p>
                 </div>
                 <Card>
                    <CardHeader>
                       <CardTitle className="text-base">Raw Analysis Output</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground prose prose-sm dark:prose-invert max-w-none">
                       <div dangerouslySetInnerHTML={{ __html: data.raw_output.replace(/\n/g, '<br/>') }} />
                    </CardContent>
                 </Card>
              </div>
            )}

            {/* Structured Verdict Section */}
            {data.timing_verdict && (
              <>
            <div className="p-4 rounded-lg bg-secondary/50 border border-border space-y-2">
              <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">Timing Verdict</h3>
               <div className="flex items-start gap-3">
                 <TrendingUp className="w-5 h-5 text-primary mt-0.5" />
                 <div>
                   <p className="font-semibold text-lg">{data.timing_verdict}</p>
                 </div>
               </div>
            </div>

            {/* Main Analysis Tabs */}
            <Tabs defaultValue="assessment" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="assessment">Market</TabsTrigger>
                <TabsTrigger value="evidence">Evidence</TabsTrigger>
                <TabsTrigger value="critique">Problem</TabsTrigger>
              </TabsList>
              
              <TabsContent value="assessment" className="mt-4 space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Market Space Assessment</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground leading-relaxed prose prose-sm dark:prose-invert">
                    {/* Render Markdown-like text safely */}
                     <div dangerouslySetInnerHTML={{ __html: data.market_assessment?.replace(/\n/g, '<br/>') }} />
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="evidence" className="mt-4 space-y-6">
                <div>
                   <h4 className="font-medium mb-3 flex items-center gap-2">
                     <span className="w-2 h-2 rounded-full bg-blue-500"/> Macro Evidence
                   </h4>
                   <ul className="space-y-3">
                     {data.evidence_macro?.map((item: string, i: number) => (
                       <li key={i} className="text-sm text-muted-foreground bg-secondary/30 p-3 rounded-md border border-border/50">
                         {item}
                       </li>
                     ))}
                   </ul>
                </div>
                
                <div>
                   <h4 className="font-medium mb-3 flex items-center gap-2">
                     <span className="w-2 h-2 rounded-full bg-green-500"/> Micro Evidence (Customer Pain)
                   </h4>
                   <ul className="space-y-3">
                     {data.evidence_micro?.map((item: string, i: number) => (
                       <li key={i} className="text-sm text-muted-foreground bg-secondary/30 p-3 rounded-md border border-border/50">
                         "{item}"
                       </li>
                     ))}
                   </ul>
                </div>
              </TabsContent>

              <TabsContent value="critique" className="mt-4 space-y-4">
                <Card className="border-destructive/20 bg-destructive/5">
                  <CardHeader>
                     <CardTitle className="text-base text-destructive">Critique</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">
                    <div dangerouslySetInnerHTML={{ __html: data.problem_critique?.replace(/\n/g, '<br/>') }} />
                  </CardContent>
                </Card>

                <Card className="border-primary/20 bg-primary/5">
                  <CardHeader>
                     <CardTitle className="text-base text-primary">Revised Problem Statement</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm font-medium">
                     "{data.refined_problem_statement}"
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
            </>
            )}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
