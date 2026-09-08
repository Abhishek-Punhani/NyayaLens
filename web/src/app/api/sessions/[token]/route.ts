import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { verifyToken } from '@/lib/auth'

export async function GET(req: NextRequest, { params }: { params: { token: string } }) {
  let session;
  try {
    session = await prisma.caseSession.findUnique({
      where: { shareLink: params.token },
      include: {
        lawyer: { select: { firstName: true, lastName: true, phone: true } },
        calls: { orderBy: { createdAt: 'desc' } }
      }
    })
  } catch {
    session = await prisma.caseSession.findUnique({
      where: { shareLink: params.token },
      include: {
        lawyer: { select: { firstName: true, lastName: true, phone: true } }
      }
    })
  }
  if (!session) return NextResponse.json({ error: 'Session not found' }, { status: 404 })

  return NextResponse.json({
    id: session.id,
    sessionId: session.backendSessionId,
    backendSessionId: session.backendSessionId,
    shareLink: session.shareLink,
    clientName: session.clientName,
    clientPhone: session.clientPhone,
    lawyerName: `${session.lawyer.firstName} ${session.lawyer.lastName}`,
    lawyerContact: session.lawyer.phone,
    status: session.status,
    callStatus: session.callStatus,
    callSummary: session.callSummary,
    callAttempts: session.callAttempts,
    callDuration: session.callDuration,
    lastCallAt: session.lastCallAt,
    factsCount: session.factsCount,
    flagsCount: session.flagsCount,
    calls: session.calls
  })
}

export async function DELETE(req: NextRequest, { params }: { params: { token: string } }) {
  const authToken = req.cookies.get('nyaya_token')?.value || req.headers.get('authorization')?.replace('Bearer ', '')
  const payload = verifyToken(authToken || '')
  if (!payload) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const session = await prisma.caseSession.findUnique({
    where: { shareLink: params.token }
  })
  if (!session || session.lawyerId !== payload.lawyerId) {
    return NextResponse.json({ error: 'Session not found' }, { status: 404 })
  }

  // Attempt to notify FastAPI backend to free memory & cancel tasks
  const body = await req.json().catch(() => ({}))
  const backendUrl = body.backendUrl || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
  try {
    await fetch(`${backendUrl}/api/session/${session.backendSessionId}`, { method: 'DELETE' })
  } catch (err) {
    console.error('[DELETE session] Backend cleanup warning:', err)
  }

  // Delete associated calls from database
  try {
    await prisma.callLog.deleteMany({
      where: { sessionId: session.id }
    })
  } catch (err) {
    console.error('[DELETE session] CallLog cleanup warning:', err)
  }

  // Delete the case session
  await prisma.caseSession.delete({
    where: { id: session.id }
  })

  return NextResponse.json({ success: true, message: 'Client session deleted successfully' })
}

