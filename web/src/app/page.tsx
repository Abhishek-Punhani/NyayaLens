'use client'
import Link from 'next/link'
import Image from 'next/image'
import { motion } from 'framer-motion'
import { Scale, Brain, Search, Clock, FileText, ArrowRight, ShieldCheck, Zap, Quote, Star } from 'lucide-react'
import React from 'react'

function FadeIn({ children, className, delay = 0 }: { children: React.ReactNode, className?: string, delay?: number }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.6, ease: "easeOut", delay }}
    >
      {children}
    </motion.div>
  )
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0b0d0e] selection:bg-[#a8dab5] selection:text-[#06230f] overflow-x-hidden">
      
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0b0d0e]/60 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-white/5 border border-white/10">
              <Scale className="w-4 h-4 text-white" />
            </div>
            <span className="font-sans text-white font-semibold text-lg tracking-tight">NyayaLens</span>
          </div>
          <Link 
            href="/dashboard"
            className="px-5 py-2 rounded-full font-sans text-xs font-medium transition-all bg-white text-black hover:bg-gray-200"
          >
            Advocate Login
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-[100svh] flex flex-col justify-center overflow-hidden pt-16">
        <div className="pointer-events-none absolute inset-0">
          <Image
            src="/hero-bg.jpg"
            alt="NyayaLens Background"
            fill
            priority
            className="object-cover opacity-20 mix-blend-luminosity grayscale"
            style={{ maskImage: 'linear-gradient(to bottom, rgba(0,0,0,1) 30%, rgba(0,0,0,0) 100%)', WebkitMaskImage: 'linear-gradient(to bottom, rgba(0,0,0,1) 30%, rgba(0,0,0,0) 100%)' }}
          />
          <div className="absolute inset-0 [background-image:radial-gradient(1000px_circle_at_50%_0%,rgba(255,255,255,0.03),transparent_70%)]" />
        </div>

        <div className="relative max-w-5xl mx-auto px-6 text-center z-10 -translate-y-10">
          <FadeIn>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 mb-8 backdrop-blur-md">
              <span className="w-2 h-2 rounded-full bg-[#a8dab5]" />
              <span className="font-mono text-xs text-[#a1a1aa] tracking-wide">NyayaLens V5 is now live</span>
            </div>
          </FadeIn>
          
          <FadeIn delay={0.1}>
            <h1 className="font-sans text-5xl md:text-6xl lg:text-7xl font-semibold tracking-tighter text-white mb-6 leading-[1.1] md:leading-[1.05] mx-auto">
              AI-Powered Legal Intelligence <br className="hidden md:block" />
              <span className="text-transparent bg-clip-text bg-gradient-to-b from-white to-[#a1a1aa]">
                for the Modern Advocate.
              </span>
            </h1>
          </FadeIn>
          
          <FadeIn delay={0.2}>
            <p className="font-sans max-w-2xl mx-auto text-[#a1a1aa] text-lg leading-relaxed mb-10 font-normal">
              Automate client intake, conduct trauma-informed cognitive cross-examinations via voice, reconstruct incident timelines, and instantly formulate rock-solid defense strategies.
            </p>
          </FadeIn>

          <FadeIn delay={0.3}>
            <Link 
              href="/dashboard"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full font-sans text-sm font-medium transition-all bg-white text-black hover:bg-gray-200 border border-transparent hover:border-white/20"
            >
              Access Dashboard <ArrowRight className="w-4 h-4" />
            </Link>
          </FadeIn>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 bg-[#0b0d0e] relative border-t border-white/5">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />
        <div className="relative max-w-7xl mx-auto px-6">
          <FadeIn className="text-center mb-20">
            <h2 className="font-sans text-3xl md:text-4xl font-semibold text-white mb-4 tracking-tight">An intelligence suite that thinks like a lawyer.</h2>
            <p className="font-sans text-[#a1a1aa] text-base max-w-xl mx-auto">Agentic intelligence, sequential reasoning, real-time fuzziness detection, and strict two-tier isolation.</p>
          </FadeIn>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FadeIn delay={0.1}><FeatureCard icon={Brain} title="Cognitive Cross-Examination" desc="Nyaya employs the Funnel Method, engaging clients in empathetic Hindi/Hinglish to extract deep factual profiles before locking in timelines." /></FadeIn>
            <FadeIn delay={0.2}><FeatureCard icon={Search} title="Real-Time Fuzziness Detection" desc="Contradictions and missing documents are instantly flagged during the interview, forcing clients to clarify gaps before the brief reaches your desk." /></FadeIn>
            <FadeIn delay={0.3}><FeatureCard icon={Scale} title="Sequential DAG Architecture" desc="Our LangGraph backend guarantees conflict-free reasoning, analyzing FIR charges sequentially before formulating potent defense vectors." /></FadeIn>
            <FadeIn delay={0.4}><FeatureCard icon={FileText} title="Automated Packet Generation" desc="Every voice intake yields a comprehensive 7-section case packet, including WhatsApp summaries, extracted JSON nodes, and markdown briefs." /></FadeIn>
            <FadeIn delay={0.5}><FeatureCard icon={ShieldCheck} title="Strict Two-Tier Isolation" desc="Clients interact purely via a frictionless voice orb. Advocates review the data on a robust, private analytical dashboard." /></FadeIn>
            <FadeIn delay={0.6}><FeatureCard icon={Clock} title="Limitation Risk Audit" desc="The AI silently computes critical statutory limitation periods (e.g. MV Act §166(3) 6-month rules) and alerts the advocate immediately." /></FadeIn>
          </div>
        </div>
      </section>

      {/* Performance / Testimonials Section */}
      <section className="py-24 bg-[#0b0d0e] border-t border-white/5">
        <div className="max-w-7xl mx-auto px-6">
          <FadeIn className="text-center mb-20">
            <h2 className="font-sans text-3xl md:text-4xl font-semibold text-white mb-4 tracking-tight">Trusted by elite litigators.</h2>
            <p className="font-sans text-[#a1a1aa] text-base max-w-xl mx-auto">Built for the complexity of the Indian legal system.</p>
          </FadeIn>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FadeIn delay={0.1}>
              <TestimonialCard 
                quote="NyayaLens completely eliminated the 3-hour initial consultation. The JSON extraction of the timeline is flawless."
                author="Adv. Sharma"
                role="Senior Counsel, Delhi High Court"
              />
            </FadeIn>
            <FadeIn delay={0.2}>
              <TestimonialCard 
                quote="The fuzziness detection caught a massive contradiction in a client's timeline before we even filed the FIR. Saved us a perjury risk."
                author="Priya R."
                role="MACT Specialist"
              />
            </FadeIn>
            <FadeIn delay={0.3}>
              <TestimonialCard 
                quote="Finally, an AI tool that actually speaks fluent Hinglish and understands Indian Evidence Act cross-examination principles."
                author="Karan D."
                role="Managing Partner"
              />
            </FadeIn>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 relative overflow-hidden bg-[#0b0d0e] border-t border-white/5">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(255,255,255,0.03),transparent_50%)]" />
        <div className="relative max-w-4xl mx-auto px-6 text-center">
          <FadeIn>
            <h2 className="font-sans text-4xl md:text-5xl font-semibold text-white mb-6 tracking-tight">Ready to modernize your practice?</h2>
            <p className="font-sans text-[#a1a1aa] text-lg mb-10 max-w-2xl mx-auto">Stop wasting hours on manual intake. Deploy an autonomous legal agent to build your case files.</p>
            <Link 
              href="/dashboard"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full font-sans text-sm font-medium transition-all bg-white text-black hover:bg-gray-200"
            >
              Start using NyayaLens
            </Link>
          </FadeIn>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 bg-[#0b0d0e] border-t border-[rgba(255,255,255,0.07)] text-center">
        <p className="font-mono text-[#888d8f] text-xs">
          Built with precision for Indian Law. © {new Date().getFullYear()} NyayaLens.
        </p>
      </footer>

    </div>
  )
}

function FeatureCard({ icon: Icon, title, desc }: { icon: any, title: string, desc: string }) {
  return (
    <div className="p-8 rounded-2xl bg-transparent border border-white/10 hover:border-white/20 transition-all duration-300 group h-full">
      <div className="w-10 h-10 mb-6 flex items-center justify-center">
        <Icon className="w-6 h-6 text-white group-hover:scale-110 transition-transform duration-300" />
      </div>
      <h3 className="font-sans text-lg font-medium text-white mb-3 tracking-tight">{title}</h3>
      <p className="font-sans text-[#a1a1aa] text-sm leading-relaxed">{desc}</p>
    </div>
  )
}

function TestimonialCard({ quote, author, role }: { quote: string, author: string, role: string }) {
  return (
    <div className="p-8 rounded-2xl bg-transparent border border-white/10 h-full flex flex-col justify-between relative overflow-hidden">
      <Quote className="absolute top-6 right-6 w-12 h-12 text-white/[0.02]" />
      <div>
        <div className="flex gap-1 mb-6">
          {[1,2,3,4,5].map(i => <Star key={i} className="w-3.5 h-3.5 fill-white text-white" />)}
        </div>
        <p className="font-sans text-[#e1e2e3] text-sm leading-relaxed mb-8 relative z-10 font-medium">"{quote}"</p>
      </div>
      <div>
        <h4 className="font-sans text-sm font-semibold text-white">{author}</h4>
        <p className="font-sans text-xs text-[#a1a1aa]">{role}</p>
      </div>
    </div>
  )
}
