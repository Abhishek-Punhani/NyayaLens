import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { verifyToken } from '@/lib/auth'

export async function POST(req: NextRequest, { params }: { params: { token: string } }) {
  const authToken = req.cookies.get('nyaya_token')?.value || req.headers.get('authorization')?.replace('Bearer ', '')
  const payload = verifyToken(authToken || '')
  if (!payload) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const session = await prisma.caseSession.findUnique({ where: { shareLink: params.token } })
  if (!session || session.lawyerId !== payload.lawyerId) return NextResponse.json({ error: 'Not found' }, { status: 404 })

  const { backendUrl } = await req.json().catch(() => ({}))
  
  // Trigger deep analysis on FastAPI backend
  const res = await fetch(`${backendUrl || 'http://localhost:8000'}/api/session/${session.backendSessionId}/accept-case`, {
    method: 'POST'
  })
  const data = await res.json().catch(() => ({}))

  // Update status in Prisma
  await prisma.caseSession.update({
    where: { id: session.id },
    data: { status: 'ANALYSIS' }
  })

  return NextResponse.json({ status: 'analysis_started', backendResponse: data })
}
