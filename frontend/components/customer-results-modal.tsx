"use client"

import * as React from "react"
import { X, User, Building2, Loader2, ExternalLink, MapPin, Mail, Briefcase, Globe } from "lucide-react"
import ReactMarkdown from "react-markdown"
import { Button } from "@/components/ui/button"
// import { ScrollArea } from "@/components/ui/scroll-area" // Removed for improved native scrolling behavior

interface CustomerResultsModalProps {
  isOpen: boolean
  onClose: () => void
  isLoading: boolean
  customerType: "B2C" | "B2B"
  icpDescription: string
  results: any
  onRefine: () => void
}

export function CustomerResultsModal({ 
  isOpen, 
  onClose, 
  isLoading,
  customerType,
  icpDescription,
  results,
  onRefine
}: CustomerResultsModalProps) {
  
  // Lock body scroll when modal is open
  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
    return () => { document.body.style.overflow = 'unset' }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={onClose}
      />
      
      {/* Modal Dialog */}
      <div className="relative w-full max-w-6xl bg-card border border-border rounded-xl shadow-2xl animate-in fade-in zoom-in-95 duration-200 h-[85vh] flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-muted/20 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
              {customerType === 'B2C' ? (
                 <User className="w-5 h-5 text-primary" />
              ) : (
                 <Building2 className="w-5 h-5 text-primary" />
              )}
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground">Customer Reach-out Results</h2>
              <p className="text-sm text-muted-foreground max-w-md truncate">
                Searching for: {icpDescription}
              </p>
            </div>
          </div>
          
          <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full">
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Content Area */}
        <div className="flex-1 relative min-h-0">
          {isLoading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center space-y-4 bg-background z-10">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
              <p className="text-muted-foreground animate-pulse">Finding potential customers...</p>
            </div>
          ) : (
            // Native scrolling container
            <div className="absolute inset-0 overflow-y-auto p-6 scroll-smooth">
              <div className="space-y-8 pb-10">
                {results ? (
                  customerType === 'B2C' ? (
                    // --- B2C Results ---
                    <>
                      <section>
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                          <Globe className="w-5 h-5 text-blue-500" />
                          Forums & Communities
                        </h3>
                        <div className="grid gap-4 md:grid-cols-2">
                          {results.forums?.map((forum: any, i: number) => (
                            <div key={i} className="p-4 rounded-xl border border-border bg-card hover:bg-muted/30 transition-colors">
                              <div className="flex items-start justify-between mb-2">
                                <a 
                                  href={forum.url} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="font-semibold text-primary hover:underline flex items-center gap-1"
                                >
                                  {forum.name} <ExternalLink className="w-3 h-3" />
                                </a>
                              </div>
                              <div className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg">
                                <span className="font-medium text-foreground text-xs uppercase tracking-wider block mb-1">Strategy</span>
                                <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none">
                                    <ReactMarkdown>
                                        {forum.strategy}
                                    </ReactMarkdown>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </section>

                      <section>
                         <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                          <MapPin className="w-5 h-5 text-green-500" />
                          Where to Meet Potential Customers
                        </h3>
                        <div className="bg-secondary/20 rounded-xl p-5 border border-border">
                          <ul className="space-y-3">
                             {results.offline?.map((place: string, i: number) => (
                               <li key={i} className="flex gap-3 text-sm">
                                 <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-500/10 text-green-600 flex items-center justify-center text-xs font-bold">
                                   {i + 1}
                                 </span>
                                 <span className="mt-0.5 text-foreground">{place}</span>
                               </li>
                             ))}
                          </ul>
                        </div>
                      </section>
                    </>
                  ) : (
                    // --- B2B Results ---
                    <>
                      <section>
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                          <User className="w-5 h-5 text-purple-500" />
                          Key Contacts
                        </h3>
                        <div className="grid gap-4">
                          {results.key_contacts?.map((contact: any, i: number) => (
                            <div key={i} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl border border-border bg-card gap-4">
                              <div className="flex items-start gap-4">
                                <div className="w-10 h-10 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-600 font-bold shrink-0">
                                  {contact.name.charAt(0)}
                                </div>
                                <div>
                                  <h4 className="font-semibold text-foreground">{contact.name}</h4>
                                  <p className="text-sm text-muted-foreground flex items-center gap-2">
                                    <Briefcase className="w-3.5 h-3.5" />
                                    {contact.title} <span className="text-border">|</span> {contact.company}
                                  </p>
                                  {contact.email && contact.email !== "Not available" && (
                                    <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1.5 select-all">
                                      <Mail className="w-3 h-3" />
                                      {contact.email}
                                    </p>
                                  )}
                                </div>
                              </div>
                              <div className="text-sm bg-muted/50 px-3 py-2 rounded-lg max-w-xs text-muted-foreground">
                                {contact.note}
                              </div>
                            </div>
                          ))}
                        </div>
                      </section>

                      <section>
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                          <Building2 className="w-5 h-5 text-orange-500" />
                          Target Companies
                        </h3>
                        <div className="grid gap-4 md:grid-cols-2">
                           {results.target_companies?.map((company: any, i: number) => (
                             <div key={i} className="p-4 rounded-xl border border-border bg-card">
                               <div className="flex justify-between items-start mb-2">
                                 <h4 className="font-semibold text-foreground">{company.name}</h4>
                                 {company.website && (
                                   <a href={company.website} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary">
                                     <ExternalLink className="w-4 h-4" />
                                   </a>
                                 )}
                               </div>
                               <div className="space-y-1 text-sm text-muted-foreground">
                                 <p>{company.industry} • {company.size?.toLocaleString()} employees</p>
                                 <p className="flex items-center gap-1">
                                   <MapPin className="w-3 h-3" /> {company.location}
                                 </p>
                               </div>
                             </div>
                           ))}
                        </div>
                      </section>
                    </>
                  )
                ) : (
                  <div className="text-center py-10 text-muted-foreground">No results found based on your request.</div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border flex justify-end gap-3 bg-muted/20">
           <Button variant="outline" onClick={onRefine}>
             Refine Search
           </Button>
           <Button onClick={onClose}>
             Done
           </Button>
        </div>
        
      </div>
    </div>
  )
}
