import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function POST(req: NextRequest, { params }: { params: { token: string } }) {
  await prisma.caseSession.update({
    where: { shareLink: params.token },
    data: { status: 'DONE' }
  })
  return NextResponse.json({ success: true })
}
