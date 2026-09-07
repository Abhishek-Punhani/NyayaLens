'use client'
import { useAuth } from '@/hooks/useAuth'
import { AuthPage } from './AuthPage'
import { DashboardLayout } from './DashboardLayout'
import { motion } from 'framer-motion'

export function LawyerDashboardPage() {
  const { lawyer, loading } = useAuth()

  if (loading) {
    return (
      <div className="h-screen bg-[#0b0d0e] flex items-center justify-center">
        <motion.div 
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-6 h-6 border-2 border-[#a8dab5] border-t-transparent rounded-full animate-spin" 
        />
      </div>
    )
  }

  if (!lawyer) return <AuthPage />
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="h-full"
    >
      <DashboardLayout lawyer={lawyer} />
    </motion.div>
  )
}
