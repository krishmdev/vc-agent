
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { VCReport } from "@/lib/store"
import { AlertTriangle, CheckCircle, Target, ArrowRight } from "lucide-react"

interface VCFeedbackCardProps {
  report: VCReport
}

export function VCFeedbackCard({ report }: VCFeedbackCardProps) {
  return (
    <Card className="border-indigo-200 dark:border-indigo-900/50 bg-indigo-50/50 dark:bg-indigo-950/10 mb-8">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-indigo-700 dark:text-indigo-300">
          <Target className="w-5 h-5" />
          Sequoia Partner Feedback
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Diagnosis */}
        <div>
          <h4 className="text-sm font-semibold text-indigo-900 dark:text-indigo-100 uppercase tracking-wider mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            The Hard Truth
          </h4>
          <p className="text-indigo-800 dark:text-indigo-200 text-lg leading-relaxed font-medium">
            "{report.diagnosis}"
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Strengths */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-green-700 dark:text-green-400 uppercase tracking-wider flex items-center gap-2">
              <CheckCircle className="w-3 h-3" />
              Strengths
            </h4>
            <ul className="space-y-2">
              {report.strengths.slice(0, 3).map((item, i) => (
                <li key={i} className="text-sm text-foreground/80 flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 mt-1.5 flex-shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Gaps */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="w-3 h-3" />
              Gaps
            </h4>
            <ul className="space-y-2">
              {report.gaps.slice(0, 3).map((item, i) => (
                <li key={i} className="text-sm text-foreground/80 flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 flex-shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

           {/* Next Steps */}
           <div className="space-y-3">
            <h4 className="text-xs font-semibold text-primary uppercase tracking-wider flex items-center gap-2">
              <ArrowRight className="w-3 h-3" />
              Next Moves
            </h4>
            <ul className="space-y-2">
              {report.nextSteps.slice(0, 3).map((item, i) => (
                <li key={i} className="text-sm text-foreground/80 flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 flex-shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
