import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function POST(
  req: NextRequest,
  { params }: { params: { token: string } }
) {
  try {
    const session = await prisma.caseSession.findUnique({
      where: { shareLink: params.token }
    })

    if (!session) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 })
    }

    const updatedSession = await prisma.caseSession.update({
      where: { id: session.id },
      data: {
        callStatus: 'IN_PROGRESS',
        callAttempts: { increment: 1 },
        lastCallAt: new Date()
      }
    })

    return NextResponse.json({ success: true, session: updatedSession })
  } catch (error: any) {
    console.error('Failed to update call start:', error)
    return NextResponse.json(
      { error: error?.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
