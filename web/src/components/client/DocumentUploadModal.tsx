'use client'
import React, { useState, useRef } from 'react'
import { X, Upload, CheckCircle, Loader2, AlertCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface PendingDoc { docId: string; docType: string }
interface Props {
  pendingDocs: PendingDoc[]
  sessionId: string
  backendUrl: string
  onDocUploaded: (docId: string) => void
  onClose: () => void
}

export function DocumentUploadModal({ pendingDocs, sessionId, backendUrl, onDocUploaded, onClose }: Props) {
  const [uploadStatus, setUploadStatus] = useState<Record<string, 'idle' | 'uploading' | 'done' | 'error'>>({})
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({})

  const handleFileSelect = async (doc: PendingDoc, file: File) => {
    setUploadStatus(s => ({ ...s, [doc.docId]: 'uploading' }))
    try {
      const form = new FormData()
      form.append('session_id', sessionId)
      form.append('doc_type', doc.docType)
      form.append('file', file)
      const res = await fetch(`${backendUrl}/api/upload-document`, { method: 'POST', body: form })
      if (!res.ok) throw new Error('Upload failed')
      setUploadStatus(s => ({ ...s, [doc.docId]: 'done' }))
      setTimeout(() => onDocUploaded(doc.docId), 1200)
    } catch {
      setUploadStatus(s => ({ ...s, [doc.docId]: 'error' }))
    }
  }

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm" 
          onClick={onClose} 
        />
        
        {/* Modal */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="relative w-full max-w-md mx-auto rounded-2xl overflow-hidden shadow-2xl" 
          style={{ background: '#111315', border: '1px solid rgba(255,255,255,0.08)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-[rgba(255,255,255,0.04)] bg-[#141719]/50">
            <div>
              <h2 className="font-mono text-[#e1e2e3] font-bold text-sm tracking-wide">Document Upload Required</h2>
              <p className="font-mono text-[#888d8f] text-xs mt-1">Nyaya needs these documents to proceed</p>
            </div>
            <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full text-[#888d8f] hover:text-[#e1e2e3] hover:bg-[rgba(255,255,255,0.05)] transition-all">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Doc list */}
          <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto custom-scrollbar">
            {pendingDocs.map(doc => {
              const status = uploadStatus[doc.docId] || 'idle'
              return (
                <motion.div 
                  layout
                  key={doc.docId} 
                  className="rounded-xl p-5 transition-all duration-300" 
                  style={{ 
                    background: status === 'done' ? 'rgba(52,211,153,0.03)' : '#0b0d0e', 
                    border: `1px solid ${status === 'done' ? 'rgba(52,211,153,0.2)' : 'rgba(255,255,255,0.05)'}` 
                  }}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <p className="font-mono text-[#e1e2e3] text-sm font-bold capitalize tracking-tight">{doc.docType.replace(/_/g, ' ')}</p>
                      <p className="font-mono text-[#888d8f] text-[10px] mt-1 uppercase tracking-wider">Photo or scan accepted</p>
                    </div>
                    {status === 'done' && (
                      <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }}>
                        <CheckCircle className="w-5 h-5 text-emerald-400" />
                      </motion.div>
                    )}
                    {status === 'error' && <AlertCircle className="w-5 h-5 text-red-400" />}
                    {status === 'uploading' && <Loader2 className="w-5 h-5 text-[#a8dab5] animate-spin" />}
                  </div>
                  {status !== 'done' && (
                    <>
                      <input
                        ref={el => { inputRefs.current[doc.docId] = el }}
                        type="file"
                        accept="image/*,application/pdf"
                        className="hidden"
                        onChange={e => { const f = e.target.files?.[0]; if (f) handleFileSelect(doc, f) }}
                      />
                      <button
                        onClick={() => inputRefs.current[doc.docId]?.click()}
                        disabled={status === 'uploading'}
                        className="w-full flex items-center justify-center gap-2 py-3 rounded-lg font-mono text-xs transition-all disabled:opacity-50 hover:bg-[#a8dab5]/20 group"
                        style={{ background: 'rgba(168,218,181,0.1)', border: '1px solid rgba(168,218,181,0.3)', color: '#a8dab5' }}
                      >
                        <Upload className="w-4 h-4 transition-transform group-hover:-translate-y-0.5" />
                        {status === 'uploading' ? 'Uploading...' : 'Select File'}
                      </button>
                      {status === 'error' && <p className="font-mono text-red-400 text-[10px] mt-2 text-center">Upload failed. Please try again.</p>}
                    </>
                  )}
                  {status === 'done' && (
                    <motion.p 
                      initial={{ opacity: 0, y: 5 }} 
                      animate={{ opacity: 1, y: 0 }} 
                      className="font-mono text-emerald-400 text-xs text-center"
                    >
                      Uploaded successfully ✓
                    </motion.p>
                  )}
                </motion.div>
              )
            })}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
