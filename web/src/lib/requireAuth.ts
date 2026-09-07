import { NextRequest } from 'next/server'
import { verifyToken } from './auth'

export function getAuthPayload(req: NextRequest) {
  const token = req.cookies.get('nyaya_token')?.value || req.headers.get('authorization')?.replace('Bearer ', '')
  if (!token) return null
  return verifyToken(token)
}
