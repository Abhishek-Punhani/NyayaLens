import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function GET(req: NextRequest, { params }: { params: { token: string } }) {
  const session = await prisma.caseSession.findUnique({
    where: { shareLink: params.token },
    include: { lawyer: { select: { firstName: true, lastName: true, phone: true } } }
  })
  if (!session) return NextResponse.json({ error: 'Session not found' }, { status: 404 })

  return NextResponse.json({
    sessionId: session.backendSessionId,
    lawyerName: `${session.lawyer.firstName} ${session.lawyer.lastName}`,
    lawyerContact: session.lawyer.phone,
    status: session.status
  })
}
