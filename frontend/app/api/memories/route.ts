import { NextResponse } from 'next/server'
import { AGENT_SERVICE_URL, isOffline } from '@/lib/services'

const MEM0_API_KEY = process.env.MEM0_API_KEY
const MEM0_USER_ID = process.env.MEM0_USER_ID || 'sequoia-mentor-agent'

// Offline mode reads the local SQLite store through the voice agent server instead of Mem0.
async function offlineMemories() {
    try {
        const response = await fetch(`${AGENT_SERVICE_URL}/memories?user_id=${encodeURIComponent(MEM0_USER_ID)}`)
        const data = await response.json()
        return NextResponse.json({ memories: data.memories ?? [] })
    } catch (error) {
        return NextResponse.json({ memories: [], error: String(error) })
    }
}

export async function GET() {
    if (isOffline()) return offlineMemories()


    if (!MEM0_API_KEY) {
        console.error('[MEMORIES API] No MEM0_API_KEY found in env!')
        return NextResponse.json({ memories: [], error: 'No API key configured' })
    }

    try {
        // Use GET with query params to fetch all memories for user
        const url = `https://api.mem0.ai/v1/memories/?user_id=${encodeURIComponent(MEM0_USER_ID)}&page_size=50`

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Token ${MEM0_API_KEY}`,
                'Content-Type': 'application/json',
            },
        })


        if (!response.ok) {
            const error = await response.text()
            console.error('[MEMORIES API] Mem0 API error:', error)
            return NextResponse.json({ memories: [], error })
        }

        const data = await response.json()

        // Extract the memories from the response - try different formats
        let memories = []
        if (Array.isArray(data)) {
            memories = data
        } else if (data.results && Array.isArray(data.results)) {
            memories = data.results
        } else if (data.memories && Array.isArray(data.memories)) {
            memories = data.memories
        }


        if (memories.length > 0) {
        }

        return NextResponse.json({ memories })
    } catch (error) {
        console.error('[MEMORIES API] Failed to fetch memories:', error)
        return NextResponse.json({ memories: [], error: String(error) })
    }
}

