import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { verifyToken } from '@/lib/auth'
import { nanoid } from 'nanoid' // npm install nanoid

export async function GET(req: NextRequest) {
  const token = req.cookies.get('nyaya_token')?.value || req.headers.get('authorization')?.replace('Bearer ', '')
  const payload = verifyToken(token || '')
  if (!payload) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const sessions = await prisma.caseSession.findMany({
    where: { lawyerId: payload.lawyerId },
    orderBy: { createdAt: 'desc' }
  })
  return NextResponse.json({ sessions })
}

export async function POST(req: NextRequest) {
  const token = req.cookies.get('nyaya_token')?.value || req.headers.get('authorization')?.replace('Bearer ', '')
  const payload = verifyToken(token || '')
  if (!payload) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { clientName, clientPhone, backendUrl } = await req.json()

  // 1. Create a backend FastAPI session
  const backendRes = await fetch(`${backendUrl || 'http://localhost:8000'}/api/session/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ language: 'hi', lawyer_name: '', lawyer_contact: '' })
  })
  const backendData = await backendRes.json()
  const backendSessionId = backendData.thread_id

  // 2. Generate a unique shareable link token
  const shareToken = nanoid(16)

  // 3. Store in Prisma
  const session = await prisma.caseSession.create({
    data: {
      lawyerId: payload.lawyerId,
      clientName,
      clientPhone,
      backendSessionId,
      shareLink: shareToken,
      status: 'INTAKE'
    }
  })

  return NextResponse.json({ session, shareLink: `${process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'}/call?token=${shareToken}` }, { status: 201 })
}
