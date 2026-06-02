import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import Header from './components/Header';
import Hero from './components/Hero';
import StateSimulator from './components/StateSimulator';
import BentoGrid from './components/BentoGrid';
import DocsSection from './components/DocsSection';
import Footer from './components/Footer';
import { Terminal, Copy, Check, ArrowRight, BookOpen, Fingerprint } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('home');
  const [copiedInstall, setCopiedInstall] = useState<boolean>(false);

  const handleCopyInstall = () => {
    navigator.clipboard.writeText('npx alive-ai@latest init my-ai');
    setCopiedInstall(true);
    setTimeout(() => {
      setCopiedInstall(false);
    }, 1800);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-white">
      
      {/* Header Bar */}
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Zones Selection using AnimatePresence transitions */}
      <main className="flex-grow">
        <AnimatePresence mode="wait">
          
          {/* HOME TAB */}
          {activeTab === 'home' && (
            <motion.div
              key="home"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.35, ease: 'easeOut' }}
            >
              {/* Grand landing, titles, and interactive Wireframe map */}
              <Hero setActiveTab={setActiveTab} />

              {/* Bento Grid highlighting the full collection of Alive-AI layers */}
              <BentoGrid />

              {/* Quick CLI Get Started Sandbox CTA */}
              <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
                <div className="rounded-2xl border border-slate-900 bg-gradient-to-r from-slate-950 via-slate-900/60 to-slate-950 p-6 sm:p-8 lg:p-12 relative overflow-hidden flex flex-col lg:flex-row items-center justify-between gap-8 shadow-2xl">
                  
                  {/* Neon border lines */}
                  <div className="absolute top-0 bottom-0 left-0 w-0.5 bg-gradient-to-b from-cyan-500 to-indigo-500 opacity-60" />

                  <div className="max-w-xl space-y-3.5">
                    <span className="font-mono text-[9px] font-bold text-cyan-400 tracking-widest uppercase">RAPID TERMINAL ADOPTION</span>
                    <h3 className="font-sans text-2xl sm:text-3xl font-black text-white tracking-tight">Ready to activate your local heart core?</h3>
                    <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed font-normal">
                      Scaffold an isolated Alive-AI project with preconfigured environment trees, database variables, directives, and instructions. Starts running immediately on Ollama or remote LLMs.
                    </p>
                  </div>

                  {/* Installer Terminal Action Panel */}
                  <div className="w-full lg:w-auto shrink-0 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                    <div className="bg-slate-950 rounded-xl border border-slate-800 p-4 flex items-center justify-between gap-4 font-mono text-xs sm:text-sm min-w-80 shadow-inner">
                      <span className="text-slate-200 select-all">npx alive-ai@latest init my-ai</span>
                      <button
                        type="button"
                        onClick={handleCopyInstall}
                        className="text-slate-500 hover:text-white transition-colors cursor-pointer"
                        title="Copy install command"
                        id="copy-install-btn"
                      >
                        {copiedInstall ? (
                          <Check className="h-4 w-4 text-emerald-400" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        setActiveTab('docs');
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }}
                      className="flex items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 font-sans text-xs sm:text-sm font-bold text-slate-950 hover:bg-slate-100 transition-colors"
                      id="home-docs-shortcut-btn"
                    >
                      <BookOpen className="h-4 w-4" />
                      Read CLI Core Docs
                    </button>
                  </div>

                </div>
              </section>

            </motion.div>
          )}

          {/* SIMULATOR TAB */}
          {activeTab === 'simulator' && (
            <motion.div
              key="simulator"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.35, ease: 'easeOut' }}
            >
              <StateSimulator />
            </motion.div>
          )}

          {/* DOCUMENTATION TAB */}
          {activeTab === 'docs' && (
            <motion.div
              key="docs"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.35, ease: 'easeOut' }}
            >
              <DocsSection />
            </motion.div>
          )}

        </AnimatePresence>
      </main>

      {/* Footer Bar */}
      <Footer setActiveTab={setActiveTab} />

    </div>
  );
}
