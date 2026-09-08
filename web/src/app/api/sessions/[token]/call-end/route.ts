import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function POST(
  req: NextRequest,
  { params }: { params: { token: string } }
) {
  try {
    const body = await req.json().catch(() => ({}))
    const { status = 'disconnected', duration = 0 } = body

    const session = await prisma.caseSession.findUnique({
      where: { shareLink: params.token }
    })

    if (!session) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 })
    }

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
    let summary: string | null = null
    let factsCount = session.factsCount || 0
    let flagsCount = session.flagsCount || 0

    // Try fetching summary from FastAPI backend /call-summary
    try {
      const res = await fetch(`${backendUrl}/api/session/${session.backendSessionId}/call-summary`, {
        signal: AbortSignal.timeout(4000)
      })
      if (res.ok) {
        const data = await res.json()
        if (data.summary) summary = data.summary
        if (typeof data.facts_count === 'number') factsCount = data.facts_count
        if (typeof data.flags_count === 'number') flagsCount = data.flags_count
      } else {
        throw new Error(`Call-summary returned ${res.status}`)
      }
    } catch (err) {
      // Fallback: fetch session state directly from /api/session/${backendSessionId}
      try {
        const res = await fetch(`${backendUrl}/api/session/${session.backendSessionId}`, {
          signal: AbortSignal.timeout(4000)
        })
        if (res.ok) {
          const data = await res.json()
          const facts = data?.state?.facts || []
          const flags = data?.state?.fuzziness_flags || []
          factsCount = facts.length
          flagsCount = flags.filter((f: any) => !f.resolved).length

          // Formulate summary from facts if available
          if (facts.length > 0) {
            const keyFacts = facts.slice(0, 6).map((f: any) => `${f.field?.replace(/_/g, ' ')}: ${f.value}`).join('; ')
            summary = `Captured ${facts.length} facts. Key details: ${keyFacts}`
          }
        }
      } catch (fallbackErr) {
        console.warn('Backend call-summary fallback failed:', fallbackErr)
      }
    }

    if (!summary) {
      summary = `Call ${status.toLowerCase()} (${Math.round(duration)}s). ${factsCount} facts captured.`
    }

    const normalizedStatus = (status || 'disconnected').toUpperCase()
    const callDurationIncrement = typeof duration === 'number' ? Math.max(0, Math.round(duration)) : 0

    const [updatedSession, callLog] = await prisma.$transaction([
      prisma.caseSession.update({
        where: { id: session.id },
        data: {
          callStatus: normalizedStatus,
          callDuration: (session.callDuration || 0) + callDurationIncrement,
          callSummary: summary,
          factsCount,
          flagsCount,
          callAttempts: { increment: 1 },
          lastCallAt: new Date(),
        }
      }),
      prisma.callLog.create({
        data: {
          sessionId: session.id,
          status: normalizedStatus,
          duration: callDurationIncrement,
          summary,
          factsCount
        }
      })
    ])

    return NextResponse.json({ success: true, session: updatedSession, callLog })
  } catch (error: any) {
    console.error('Failed to process call-end:', error)
    return NextResponse.json(
      { error: error?.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
