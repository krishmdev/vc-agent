import { NextRequest, NextResponse } from 'next/server'
import { isOffline } from '@/lib/services'

// Field schema with keywords for matching
const FIELD_SCHEMA = [
    // --- TIER 1: FOUNDER (Right to Exist) ---
    {
        moduleId: 'founder',
        questionId: 'unique-insight',
        keywords: ['unique', 'insight', 'secret', 'advantage', 'know', 'others don\'t', 'earned secret']
    },
    {
        moduleId: 'founder',
        questionId: 'why-you',
        keywords: ['why you', 'founder', 'fit', 'background', 'suited', 'experience', 'qualified', 'personal connection']
    },
    {
        moduleId: 'founder',
        questionId: 'why-now',
        keywords: ['why now', 'timing', 'change', 'shift', 'market', 'trend', 'technological shift']
    },
    {
        moduleId: 'founder',
        questionId: 'commitment',
        keywords: ['commit', '10 years', 'decade', 'long term', 'life', 'devote', 'time horizon']
    },

    // --- TIER 2: PROBLEM (Urgency) ---
    {
        moduleId: 'problem',
        questionId: 'hair-on-fire',
        keywords: ['hair on fire', 'urgent', 'burning', 'critical', 'emergency', 'immediate', 'painful']
    },
    {
        moduleId: 'problem',
        questionId: 'workarounds',
        keywords: ['workaround', 'hack', 'manual', 'spreadsheet', 'glue', 'fixing', 'status quo', 'broken process']
    },
    {
        moduleId: 'problem',
        questionId: 'imperfect-solution',
        keywords: ['imperfect', 'flawed', 'broken', 'bad solution', 'still use', 'desperate']
    },
    {
        moduleId: 'problem',
        questionId: 'cost-of-inaction',
        keywords: ['cost', 'inaction', 'loss', 'losing', 'money', 'time', 'expensive']
    },

    // --- TIER 3: CUSTOMER (Clarity) ---
    {
        moduleId: 'customer',
        questionId: 'high-expectation-customer',
        keywords: ['high expectation', 'demanding', 'best customer', 'ideal', 'user', 'persona', 'target']
    },
    {
        moduleId: 'customer',
        questionId: 'reach-without-intros',
        keywords: ['reach', 'distribution', 'channel', 'find', 'acquire', 'cold', 'outbound', 'inbound']
    },
    {
        moduleId: 'customer',
        questionId: 'common-traits',
        keywords: ['common', 'trait', 'pattern', 'shared', 'characteristic', 'demographics', 'psychographics']
    },
    {
        moduleId: 'customer',
        questionId: 'buyer-vs-user',
        keywords: ['buyer', 'user', 'decision', 'purchaser', 'check writer', 'stakeholder']
    },

    // --- TIER 4: PRODUCT (Differentiation) ---
    {
        moduleId: 'product',
        questionId: 'eureka-moment',
        keywords: ['eureka', 'breakthrough', 'moment', 'realize', 'discovery', 'realization']
    },
    {
        moduleId: 'product',
        questionId: 'different-vs-better',
        keywords: ['different', 'better', 'category', 'new way', 'old way', '10x', 'improvement']
    },
    {
        moduleId: 'product',
        questionId: 'wedge',
        keywords: ['wedge', 'entry', 'start', 'niche', 'foothold', 'initial feature', 'mvc']
    },
    {
        moduleId: 'product',
        questionId: 'lightbulb-moment',
        keywords: ['lightbulb', 'get it', 'click', 'understand', 'aha', 'moment of truth']
    },

    // --- TIER 5: MARKET (Viability) ---
    {
        moduleId: 'market',
        questionId: 'willingness-to-pay',
        keywords: ['pay', 'willing', 'budget', 'price', 'money', 'contract', 'purchasing power']
    },
    {
        moduleId: 'market',
        questionId: 'path-to-revenue',
        keywords: ['revenue', '500m', 'scale', 'growth', 'path', 'market size', 'money']
    },
    {
        moduleId: 'market',
        questionId: 'defensibility',
        keywords: ['defensible', 'moat', 'protect', 'copy', 'barrier', 'network effect', 'lock-in']
    },
    {
        moduleId: 'market',
        questionId: 'winning-plan',
        keywords: ['win', 'strategy', 'beat', 'alternatives', 'competition', 'competitors']
    },
]

// --- TOKENIZATION & JACCARD SIMILARITY ---

function tokenize(text: string): Set<string> {
    return new Set(
        text.toLowerCase()
            .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, "") // Remove punctuation
            .split(/\s+/) // Split by whitespace
            .filter(t => t.length > 2) // Filter tiny words
    )
}

function calculateJaccardIndex(textA: string, keywords: string[]): number {
    const tokensA = tokenize(textA)
    const tokensB = new Set(keywords.map(k => k.toLowerCase()))

    let intersection = 0
    tokensB.forEach(t => {
        // Check for partial matches or exact matches in the text tokens
        // For robustness, if a keyword is "market size", we check if tokensA has "market" AND "size"? 
        // Or simplified: just bag of words intersection.
        if (tokensA.has(t)) {
            intersection++
        } else {
            // Fuzzy check: if keyword is a phrase like "pain point", check if text contains it
            if (t.includes(' ')) {
                if (textA.toLowerCase().includes(t)) intersection += 2 // Boost for phrase match
            }
        }
    })

    const union = tokensA.size + tokensB.size - intersection
    return union === 0 ? 0 : intersection / union
}

export async function POST(request: NextRequest) {
    console.log('[EXTRACT-FIELDS] Starting robust field extraction...')

    try {
        const { memories } = await request.json()
        console.log('[EXTRACT-FIELDS] Received memories count:', memories?.length || 0)

        if (!memories || memories.length === 0) {
            return NextResponse.json({ fields: [] })
        }

        // Helper to extract text
        const getMemoryText = (m: Record<string, unknown>): string => {
            if (typeof m.memory === 'string') return m.memory
            if (typeof m.content === 'string') return m.content
            if (typeof m.text === 'string') return m.text
            if (typeof m.data === 'string') return m.data
            if (m.memory && typeof m.memory === 'object') return JSON.stringify(m.memory)
            return ''
        }

        const cleanMemories = memories.map(getMemoryText).filter((t: string) => t.length > 10)

        const extractedFields: Array<{ moduleId: string; questionId: string; value: string }> = []
        const lowConfidenceFields: typeof FIELD_SCHEMA = []

        // 1. LOCAL PASS: Jaccard Similarity
        for (const field of FIELD_SCHEMA) {
            let bestScore = 0
            let bestMemoryText = ''

            cleanMemories.forEach((memoryText: string) => {
                const score = calculateJaccardIndex(memoryText, field.keywords)
                // Boost score if direct keyword match is found
                const keywordMatchCount = field.keywords.filter(k => memoryText.toLowerCase().includes(k.toLowerCase())).length
                const adjustedScore = score + (keywordMatchCount * 0.1)

                if (adjustedScore > bestScore) {
                    bestScore = adjustedScore
                    bestMemoryText = memoryText
                }
            })

            // Threshold for "Good Enough" without LLM
            // 0.2 Jaccard is decent for short text. 
            if (bestScore >= 0.25) {
                console.log(`[EXTRACT-FIELDS] ✅ Matched ${field.questionId} (Score: ${bestScore.toFixed(2)})`)
                extractedFields.push({
                    moduleId: field.moduleId,
                    questionId: field.questionId,
                    value: bestMemoryText,
                })
            } else {
                // If it's a critical field or score is non-zero but weak, mark for fallback
                lowConfidenceFields.push(field)
            }
        }

        // 2. LLM FALLBACK (Only if needed)
        // We only call LLM if we have fields that weren't confidently matched
        // AND we have some memories to analyze.
        // Using Gemini instead of OpenAI to avoid rate limits
        if (lowConfidenceFields.length > 0 && process.env.GEMINI_API_KEY && !isOffline()) {
            console.log(`[EXTRACT-FIELDS] ⚠️ ${lowConfidenceFields.length} fields failed local match. Attempting Gemini extraction...`)

            // Limit to top 5 missing fields to save tokens/time if list is huge
            const targetFields = lowConfidenceFields.slice(0, 5)
            const combinedMemories = cleanMemories.join("\n- ")

            const prompt = `You are an extraction engine.
Context (User Memories):
${combinedMemories}

Task: Extract values for the following fields based on the memories.
Fields to extract:
${targetFields.map(f => `- ${f.questionId} (Keywords: ${f.keywords.join(', ')})`).join('\n')}

Return a JSON object where keys are questionIds and values are the extracted answer. 
If no information is found for a field, omit it.
Output ONLY valid JSON, no markdown.`

            try {
                const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${process.env.GEMINI_API_KEY}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        contents: [{ parts: [{ text: prompt }] }],
                        generationConfig: {
                            responseMimeType: "application/json"
                        }
                    })
                })

                if (response.ok) {
                    const data = await response.json()
                    const resultText = data.candidates?.[0]?.content?.parts?.[0]?.text || '{}'
                    const result = JSON.parse(resultText)

                    Object.entries(result).forEach(([key, value]) => {
                        if (value && typeof value === 'string' && value.length > 5 && value !== "not found") {
                            const fieldDef = FIELD_SCHEMA.find(f => f.questionId === key)
                            if (fieldDef) {
                                console.log(`[EXTRACT-FIELDS] ✨ Gemini extracted ${key}`)
                                extractedFields.push({
                                    moduleId: fieldDef.moduleId,
                                    questionId: key,
                                    value: value,
                                })
                            }
                        }
                    })
                } else {
                    console.error('[EXTRACT-FIELDS] Gemini Call failed:', response.status, await response.text())
                }
            } catch (llmError) {
                console.error('[EXTRACT-FIELDS] Gemini Error:', llmError)
            }
        }

        console.log(`[EXTRACT-FIELDS] Total fields extracted: ${extractedFields.length}`)
        return NextResponse.json({ fields: extractedFields })
    } catch (error) {
        console.error('[EXTRACT-FIELDS] Error:', error)
        return NextResponse.json({ error: 'Failed to extract fields' }, { status: 500 })
    }
}
