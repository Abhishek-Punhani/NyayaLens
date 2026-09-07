import { Suspense } from 'react'
import { ClientCallPage } from '@/components/client/ClientCallPage'

export default function CallPage() {
  return (
    <Suspense fallback={<div className="h-screen bg-[#0b0d0e] flex items-center justify-center text-[#888d8f] font-mono text-sm">Loading session...</div>}>
      <ClientCallPage />
    </Suspense>
  )
}
