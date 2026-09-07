'use client'
import { useState, useEffect, useCallback } from 'react'

interface Lawyer {
  id: string
  firstName: string
  lastName: string
  email: string
  phone?: string
  barCouncilId?: string
}

export function useAuth() {
  const [lawyer, setLawyer] = useState<Lawyer | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchMe = useCallback(async () => {
    try {
      const res = await fetch('/api/auth/me')
      if (res.ok) {
        const data = await res.json()
        setLawyer(data.lawyer)
      } else {
        setLawyer(null)
      }
    } catch {
      setLawyer(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchMe() }, [fetchMe])

  const login = async (email: string, password: string) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Login failed')
    setLawyer(data.lawyer)
    return data
  }

  const register = async (fields: { firstName: string; lastName: string; email: string; password: string; phone?: string; barCouncilId?: string }) => {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(fields)
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Registration failed')
    setLawyer(data.lawyer)
    return data
  }

  const logout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' })
    setLawyer(null)
  }

  return { lawyer, loading, login, register, logout, refetch: fetchMe }
}
