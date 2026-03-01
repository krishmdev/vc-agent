
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { AlertTriangle, CheckCircle, Target, HelpCircle, ArrowRight } from "lucide-react"
import { VCReport } from "@/lib/store"

interface VCReportModalProps {
  isOpen: boolean
  onClose: () => void
  report: VCReport | null
}

export function VCReportModal({ isOpen, onClose, report }: VCReportModalProps) {
  if (!report) return null

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[85vh] p-0 gap-0 overflow-hidden">
        <DialogHeader className="p-6 pb-4 border-b bg-muted/40">
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            <Target className="w-5 h-5 text-indigo-600" />
            Sequoia Partner Feedback
          </DialogTitle>
          <DialogDescription>
            A candid analysis of your pitch based on Sequoia&apos;s evaluation framework.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="flex-1 p-6 max-h-[calc(85vh-80px)]">
          <div className="space-y-8">
            {/* Diagnosis */}
            <div className="bg-indigo-50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-900/50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-indigo-900 dark:text-indigo-100 uppercase tracking-wider mb-2 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                The Hard Truth (Diagnosis)
              </h3>
              <p className="text-indigo-800 dark:text-indigo-200 text-lg leading-relaxed font-medium">
                &ldquo;{report.diagnosis}&rdquo;
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              {/* Strengths */}
              <div>
                <h3 className="text-sm font-semibold text-green-700 dark:text-green-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  What&apos;s Working (Strengths)
                </h3>
                <ul className="space-y-3">
                  {report.strengths.map((strength, i) => (
                    <li key={i} className="flex items-start gap-3 bg-green-50 dark:bg-green-950/10 p-3 rounded-md border border-green-100 dark:border-green-900/20">
                      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 flex items-center justify-center text-xs font-bold">
                        {i + 1}
                      </span>
                      <span className="text-sm text-foreground/90">{strength}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Gaps */}
              <div>
                <h3 className="text-sm font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Major Gaps
                </h3>
                <ul className="space-y-3">
                  {report.gaps.map((gap, i) => (
                    <li key={i} className="flex items-start gap-3 bg-amber-50 dark:bg-amber-950/10 p-3 rounded-md border border-amber-100 dark:border-amber-900/20">
                      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 flex items-center justify-center text-xs font-bold">
                        {i + 1}
                      </span>
                      <span className="text-sm text-foreground/90">{gap}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Terrifying Questions */}
            <div>
              <h3 className="text-sm font-semibold text-red-700 dark:text-red-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                <HelpCircle className="w-4 h-4" />
                Unanswered &ldquo;Terrifying Questions&rdquo;
              </h3>
              <div className="grid gap-3">
                {report.terrifyingQuestions.map((question, i) => (
                  <div key={i} className="bg-background border border-border p-4 rounded-lg shadow-sm">
                    <p className="font-medium text-foreground">&ldquo;{question}&rdquo;</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Next Steps */}
            <div>
               <h3 className="text-sm font-semibold text-primary uppercase tracking-wider mb-4 flex items-center gap-2">
                <ArrowRight className="w-4 h-4" />
                Next Moves
              </h3>
               <ul className="space-y-2">
                {report.nextSteps.map((step, i) => (
                  <li key={i} className="flex items-center gap-3 text-sm text-muted-foreground">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                    {step}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
