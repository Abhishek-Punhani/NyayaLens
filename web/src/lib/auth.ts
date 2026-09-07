import bcrypt from 'bcryptjs'
import jwt from 'jsonwebtoken'

const JWT_SECRET = process.env.JWT_SECRET || 'nyayalens-dev-secret-change-in-prod'
const JWT_EXPIRES_IN = '7d'

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 12)
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash)
}

export function signToken(payload: { lawyerId: string; email: string }): string {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN })
}

export function verifyToken(token: string): { lawyerId: string; email: string } | null {
  try {
    return jwt.verify(token, JWT_SECRET) as { lawyerId: string; email: string }
  } catch {
    return null
  }
}
