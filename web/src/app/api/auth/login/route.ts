import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { verifyPassword, signToken } from '@/lib/auth'

export async function POST(req: NextRequest) {
  try {
    const { email, password } = await req.json()
    if (!email || !password) {
      return NextResponse.json({ error: 'Email and password required' }, { status: 400 })
    }

    const lawyer = await prisma.lawyer.findUnique({ where: { email } })
    if (!lawyer) {
      return NextResponse.json({ error: 'Invalid credentials' }, { status: 401 })
    }

    const valid = await verifyPassword(password, lawyer.password)
    if (!valid) {
      return NextResponse.json({ error: 'Invalid credentials' }, { status: 401 })
    }

    const token = signToken({ lawyerId: lawyer.id, email: lawyer.email })
    const { password: _, ...lawyerData } = lawyer

    const response = NextResponse.json({ lawyer: lawyerData, token })
    response.cookies.set('nyaya_token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 7 * 24 * 60 * 60,
      path: '/'
    })
    return response
  } catch (err: any) {
    console.error('[login]', err)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
