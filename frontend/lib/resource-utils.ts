/**
 * Resource utilities for parsing and displaying RAG resources
 */

export interface RagResource {
    type: "resource"
    id: string
    title: string
    summary: string
    sourceFile: string
    resourceType: "founder_story" | "ai_insight" | "framework" | "article"
}

export interface DisplayResource {
    id: string
    title: string
    type: "article" | "framework" | "example" | "metric"
    description: string
    url?: string
}

// Map RAG resource types to display types
const resourceTypeMap: Record<RagResource["resourceType"], DisplayResource["type"]> = {
    founder_story: "example",
    ai_insight: "article",
    framework: "framework",
    article: "article",
}

// Known YouTube videos from Sequoia's channel (partial matches)
const SEQUOIA_YOUTUBE_VIDEOS: Record<string, string> = {
    "airbnb ft brian chesky": "https://www.youtube.com/watch?v=W608u6sBFpo",
    "doordash ft. tony xu": "https://www.youtube.com/watch?v=9LNWqvYGOQQ",
    "nvidia ft. jensen huang": "https://www.youtube.com/watch?v=OXbIiOAHzck",
    "stripe ft. patrick collison": "https://www.youtube.com/watch?v=rENO7cLcA3A",
    "dropbox ft. drew houston": "https://www.youtube.com/watch?v=tV_1pP3X4nQ",
    "paypal ft max levchin": "https://www.youtube.com/watch?v=5ZxvWBxLWUQ",
    "reddit ft. founder steve huffman": "https://www.youtube.com/watch?v=lDAQvP2Ocp4",
    "youtube ft. founder steve chen": "https://www.youtube.com/watch?v=qMWUv4gMbEc",
    "robinhood ft. vlad tenev": "https://www.youtube.com/watch?v=Hq1VH0wYQ6o",
    "hubspot ft. brian halligan": "https://www.youtube.com/watch?v=xQJvwqAqJvo",
    "mongodb ft. dev ittycheria": "https://www.youtube.com/watch?v=H5FY1VJMkAM",
    "nubank ft. david vélez": "https://www.youtube.com/watch?v=5AxvqEqWGKY",
    "block ft. jack dorsey": "https://www.youtube.com/watch?v=RzqLqPRxnNw",
    "eventbrite ft. julia hartz": "https://www.youtube.com/watch?v=R9QqKzKwcGk",
    "bolt ft. markus villig": "https://www.youtube.com/watch?v=0PF9Zq2xN4o",
    "supercell ft ilkka paananen": "https://www.youtube.com/watch?v=aGp-bMKgJQQ",
    "servicenow ft. frank slootman": "https://www.youtube.com/watch?v=B7TqLzXTZJQ",
    "uipath ft. daniel dines": "https://www.youtube.com/watch?v=Fj5V5RqG9E8",
    "natera ft. matthew rabinowitz": "https://www.youtube.com/watch?v=LdQrZVs8TnA",
    "23andme ft. anne wojcicki": "https://www.youtube.com/watch?v=3rUfJY1LN_E",
}

/**
 * Generate URL for a resource if known
 */
function generateResourceUrl(title: string, sourceFile: string): string | undefined {
    const lowerTitle = title.toLowerCase()

    // Check for known YouTube videos
    for (const [key, url] of Object.entries(SEQUOIA_YOUTUBE_VIDEOS)) {
        if (lowerTitle.includes(key) || sourceFile.toLowerCase().includes(key)) {
            return url
        }
    }

    // For AI/training data content, link to Sequoia's YouTube channel
    if (lowerTitle.includes("training data") || lowerTitle.includes("ai ascent")) {
        return "https://www.youtube.com/@Sequoia/videos"
    }

    // For general Sequoia content, link to their articles
    if (lowerTitle.includes("sequoia")) {
        return "https://www.sequoiacap.com/article/"
    }

    return undefined
}

/**
 * Convert a RAG resource to a display resource
 */
export function convertToDisplayResource(ragResource: RagResource): DisplayResource {
    return {
        id: ragResource.id,
        title: ragResource.title,
        type: resourceTypeMap[ragResource.resourceType] || "article",
        description: ragResource.summary,
        url: generateResourceUrl(ragResource.title, ragResource.sourceFile),
    }
}

/**
 * Parse a data channel message into a RagResource
 */
export function parseResourceMessage(data: Uint8Array): RagResource | null {
    try {
        const text = new TextDecoder().decode(data)
        const parsed = JSON.parse(text)

        if (parsed.type === "resource" && parsed.id && parsed.title) {
            return parsed as RagResource
        }
        return null
    } catch {
        return null
    }
}

/**
 * Deduplicate resources by ID and title similarity
 */
export function deduplicateResources(
    existing: DisplayResource[],
    newResource: DisplayResource
): DisplayResource[] {
    // Check for exact ID match
    if (existing.some((r) => r.id === newResource.id)) {
        return existing
    }

    // Check for similar titles (fuzzy match)
    const normalizedNewTitle = newResource.title.toLowerCase().replace(/[^a-z0-9]/g, "")
    if (
        existing.some((r) => {
            const normalizedExisting = r.title.toLowerCase().replace(/[^a-z0-9]/g, "")
            return normalizedExisting === normalizedNewTitle
        })
    ) {
        return existing
    }

    return [...existing, newResource]
}
