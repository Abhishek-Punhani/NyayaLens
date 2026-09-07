import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { verifyToken } from '@/lib/auth'

export async function GET(req: NextRequest) {
  const token = req.cookies.get('nyaya_token')?.value || req.headers.get('authorization')?.replace('Bearer ', '')
  if (!token) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const payload = verifyToken(token)
  if (!payload) return NextResponse.json({ error: 'Invalid token' }, { status: 401 })

  const lawyer = await prisma.lawyer.findUnique({
    where: { id: payload.lawyerId },
    select: { id: true, firstName: true, lastName: true, email: true, phone: true, barCouncilId: true, createdAt: true }
  })
  if (!lawyer) return NextResponse.json({ error: 'Lawyer not found' }, { status: 404 })

  return NextResponse.json({ lawyer })
}
