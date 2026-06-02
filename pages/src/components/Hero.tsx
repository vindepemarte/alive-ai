import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ArrowRight, BookOpen, Fingerprint, Heart, Compass, ShieldAlert, Cpu, Database, Eye } from 'lucide-react';

interface HeroProps {
  setActiveTab: (tab: string) => void;
}

export default function Hero({ setActiveTab }: HeroProps) {
  // Currently inspected node in the Architecture Wireframe
  const [selectedNode, setSelectedNode] = useState<string>('biology');

  const architectureNodes = [
    {
      id: 'sensory',
      title: '1. SENSORY STIMULUS',
      subtitle: 'Environmental & User Hooks',
      icon: Fingerprint,
      color: 'border-cyan-500 text-cyan-400 bg-cyan-950/20',
      shadow: 'shadow-cyan-500/10',
      description: 'Collects inbound chat content, timestamps, user specific settings, and tick impulses (idle silence clocks). Detects topics and emotional cues.',
      stats: [
        { label: 'Active Channels', value: 'Terminal, Telegram, WebUI' },
        { label: 'Somatic Tickers', value: '1,000ms Loop Rate' },
        { label: 'Topic Vectorization', value: 'Real-time Hybrid' }
      ]
    },
    {
      id: 'biology',
      title: '2. INTEROCEPTIVE BIOLOGY',
      subtitle: 'Circadian Phase & Hormones',
      icon: Heart,
      color: 'border-rose-500 text-rose-400 bg-rose-950/20',
      shadow: 'shadow-rose-500/10',
      description: 'Integrates Oxytocin (bonding), Dopamine (reward search), Serotonin (damping), Cortisol (stress multiplier), Melatonin (sleepiness), and Sleep Debt parameters into a somatic report.',
      stats: [
        { label: 'Circadian State', value: ' AUTHORITATIVE (File-backed)' },
        { label: 'Hormonal Decay', value: 'Exponential half-life' },
        { label: 'Biomimicry Rate', value: '5 active metrics' }
      ]
    },
    {
      id: 'affect',
      title: '3. AFFECT PROCESSOR',
      subtitle: 'PAD Emotional Grid',
      icon: Cpu,
      color: 'border-indigo-500 text-indigo-400 bg-indigo-950/20',
      shadow: 'shadow-indigo-500/10',
      description: 'Processes sensory and biological changes to map the current state across Valence (-1 to +1), Arousal (-1 to +1), and Dominance (-1 to +1). Recovers complex emotions.',
      stats: [
        { label: 'Primary Matrix', value: 'PAD coordinate projection' },
        { label: 'Complex Affects', value: '12 active states' },
        { label: 'Emotional Drift', value: 'Adaptive attraction points' }
      ]
    },
    {
      id: 'subconscious',
      title: '4. SUBCONSCIOUS DMN',
      subtitle: 'Default-Mode Networks & Conflicts',
      icon: Compass,
      color: 'border-amber-500 text-amber-400 bg-amber-950/20',
      shadow: 'shadow-amber-500/10',
      description: 'Coordinates dreams, idle reflections, dynamic curiosity parameters, and five persistent desire-vs-fear tensions (conflicts) that swing based on user interaction.',
      stats: [
        { label: 'Active Conflicts', value: '5 swings (persistent)' },
        { label: 'Dream Interval', value: '1 cycle per sleep period' },
        { label: 'Curiosity Map', value: '0.0 - 1.0 (vectorized topics)' }
      ]
    },
    {
      id: 'planner',
      title: '5. DIALOGUE PLANNER',
      subtitle: 'Inner State Compiler',
      icon: Database,
      color: 'border-teal-500 text-teal-400 bg-teal-950/20',
      shadow: 'shadow-teal-500/10',
      description: 'Compresses emotions, conflicts, somatic energy, and narrative phase into a single concise inner-state summary, feeding instructions to the LLM context.',
      stats: [
        { label: 'Prompt Delivery', value: 'Single compiled briefing block' },
        { label: 'Memory Retention', value: 'Local episodic + OpenMind hybrid' },
        { label: 'Avoidance Filters', value: 'Proactive duplication safety' }
      ]
    },
    {
      id: 'output',
      title: '6. DISPATCH & REFLECTION',
      subtitle: 'Action Loops & Autobiography',
      icon: ShieldAlert,
      color: 'border-violet-500 text-violet-400 bg-violet-950/20',
      shadow: 'shadow-violet-500/10',
      description: 'Dispatches responses via CLI or Telegram, and saves a post-response memory. Writes a reflection journal to track personal preferences and autobiographical drift.',
      stats: [
        { label: 'Response Target', value: 'Telegram Bot API / Stdout' },
        { label: 'Post-Reflection', value: 'Automated memory synthesis' },
        { label: 'Local Filesystem', value: 'Durable JSON database' }
      ]
    }
  ];

  const activeNodeData = architectureNodes.find(n => n.id === selectedNode) || architectureNodes[1];
  const ActiveNodeIcon = activeNodeData.icon;

  return (
    <div className="relative py-12 lg:py-16 overflow-hidden">
      
      {/* Decorative Grid Mesh Background */}
      <div className="absolute inset-0 z-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,#000_70%,transparent_100%)] opacity-35" />

      {/* Futuristic Background Ambient Glows */}
      <div className="absolute top-20 left-1/4 -z-10 h-96 w-96 rounded-full bg-cyan-500/5 blur-[120px]" />
      <div className="absolute bottom-10 right-1/4 -z-10 h-96 w-96 rounded-full bg-indigo-500/5 blur-[120px]" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Main Branding Title Area */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <motion.img
            src="./assets/alive-ai.png"
            alt="Alive-AI official logo"
            initial={{ opacity: 0, scale: 0.96, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.7 }}
            className="mx-auto mb-8 h-40 w-40 object-contain sm:h-52 sm:w-52 drop-shadow-[0_0_42px_rgba(34,211,238,0.22)]"
            id="hero-official-logo"
          />
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/30 px-3.5 py-1 text-xs font-semibold text-cyan-400 mb-6"
          >
            <span className="flex h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
            <span>LOCAL-FIRST EMOTIONAL RUNTIME</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="font-sans text-4xl sm:text-5xl lg:text-6xl font-black text-white tracking-tight leading-[1.1]"
            id="hero-main-title"
          >
            Give your AI a <br className="sm:hidden" />
            <span className="bg-gradient-to-r from-cyan-400 via-indigo-400 to-rose-400 bg-clip-text text-transparent">
              digital nervous system
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mt-6 font-sans text-base sm:text-lg text-slate-400 leading-relaxed font-normal"
            id="hero-tagline"
          >
            Alive-AI is an open-source local runtime that keeps internal state alive between messages. 
            It models simulated mood, relational attachment, hormones, sleep cycles, subconscious conflict, 
            and proactive default-mode loops.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-10 flex flex-wrap items-center justify-center gap-4"
          >
            <button
              type="button"
              onClick={() => setActiveTab('simulator')}
              className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-500 to-indigo-500 px-6 py-3 font-sans text-sm font-semibold text-white shadow-lg hover:brightness-110 active:scale-98 transition-all"
              id="hero-simulate-cta"
            >
              Launch Simulator
              <ArrowRight className="h-4.5 w-4.5" />
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('docs')}
              className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/60 px-6 py-3 font-sans text-sm font-semibold text-slate-300 hover:text-white hover:border-slate-700 transition-all"
              id="hero-docs-cta"
            >
              <BookOpen className="h-4.5 w-4.5" />
              Explore Documentation
            </button>
          </motion.div>
        </div>

        {/* INTERACTIVE SYSTEM WIREFRAME SECTION */}
        <div className="mt-16 border border-slate-900 rounded-2xl bg-slate-950/40 p-6 sm:p-8 backdrop-blur-sm relative shadow-2xl">
          <div className="absolute top-4 right-4 flex items-center gap-1.5 font-mono text-[9px] text-slate-500">
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
            SYSTEM_BLUEPRINT_VER_2.8
          </div>

          <div className="flex flex-col lg:flex-row gap-8 items-start">
            
            {/* Clickable Diagram Flow Area */}
            <div className="w-full lg:w-3/5">
              <div className="flex flex-col gap-2 mb-6">
                <h3 className="font-sans text-lg font-bold text-white flex items-center gap-2">
                  <Eye className="h-5 w-5 text-cyan-400" />
                  Nervous System Wireframe Map
                </h3>
                <p className="font-sans text-xs text-slate-400">
                  Select any block of the emotional state machine below to inspect its data flow channels and active parameter multipliers.
                </p>
              </div>

              {/* Responsive Wireframe Flow Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {architectureNodes.map((node) => {
                  const NodeIcon = node.icon;
                  const isInspected = selectedNode === node.id;
                  return (
                    <button
                      key={node.id}
                      type="button"
                      onClick={() => setSelectedNode(node.id)}
                      className={`relative flex flex-col items-start rounded-xl border p-4 text-left transition-all cursor-pointer ${
                        isInspected
                          ? `${node.color} ${node.shadow} scale-102 ring-1 ring-white/10 z-10`
                          : 'border-slate-900 bg-slate-950/60 text-slate-400 hover:border-slate-800 hover:text-slate-200'
                      }`}
                      id={`wireframe-node-${node.id}`}
                    >
                      <div className="flex items-center gap-2.5">
                        <div className={`rounded-lg p-1.5 border ${isInspected ? 'border-transparent bg-white/5' : 'border-slate-800 bg-slate-900/40'}`}>
                          <NodeIcon className="h-4.5 w-4.5" />
                        </div>
                        <div>
                          <p className="font-mono text-[10px] tracking-wider opacity-80">{node.title}</p>
                          <h4 className="font-sans text-sm font-bold text-white mt-0.5">{node.subtitle}</h4>
                        </div>
                      </div>
                      
                      {/* Flow Connection Arrow Animation indicating active links */}
                      {isInspected && (
                        <div className="absolute right-3.5 top-3.5">
                          <span className="flex h-2 w-2 rounded-full bg-current animate-ping" />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* CLI Command Line Snippet */}
              <div className="mt-6 rounded-xl border border-slate-900 bg-slate-950/90 p-4 font-mono text-[11px] text-slate-400 leading-relaxed shadow-inner">
                <div className="flex items-center gap-1.5 text-[10px] text-slate-500 mb-2 border-b border-slate-900 pb-2">
                  <span className="text-cyan-400">#</span> TERMINAL INSTANT ANCHOR
                </div>
                <div className="text-slate-300">
                  <span className="text-emerald-400">npx . doctor</span> --fix <span className="text-slate-500"># verify OS dependencies, Redis caches and models</span>
                </div>
              </div>
            </div>

            {/* Wireframe Inspector Panel */}
            <div className="w-full lg:w-2/5 rounded-xl border border-slate-900 bg-slate-950/80 p-5 sm:p-6 lg:min-h-[380px] flex flex-col justify-between">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeNodeData.id}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.2 }}
                  className="flex flex-col gap-4"
                >
                  <div className="flex items-center justify-between border-b border-slate-900 pb-3">
                    <span className="font-mono text-[10px] uppercase tracking-widest text-slate-500">WIRE_DATA_LOG_SYS</span>
                    <span className="rounded bg-slate-900 px-1.5 py-0.5 font-mono text-[10px] text-cyan-400">NODE ACTIVE</span>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-slate-900/80 border border-slate-800 p-2 text-slate-300">
                      <ActiveNodeIcon className="h-5 w-5" />
                    </div>
                    <div>
                      <h4 className="font-sans text-xs font-semibold text-slate-500 uppercase tracking-widest">{activeNodeData.title}</h4>
                      <h3 className="font-sans text-base font-bold text-white mt-0.5">{activeNodeData.subtitle}</h3>
                    </div>
                  </div>

                  <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed">
                    {activeNodeData.description}
                  </p>

                  <div className="mt-2 space-y-2 border-t border-slate-900 pt-4">
                    <h5 className="font-mono text-[9px] font-bold text-slate-500 tracking-wider">ACTIVE REGISTER FEEDBACKS</h5>
                    <div className="grid grid-cols-1 gap-2.5 text-xs">
                      {activeNodeData.stats.map((stat, i) => (
                        <div key={i} className="flex items-center justify-between font-mono bg-slate-900/30 rounded p-1.5 border border-slate-900/50">
                          <span className="text-slate-500 italic text-[11px]">{stat.label}</span>
                          <span className="text-slate-200 text-right">{stat.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              </AnimatePresence>

              {/* Wireframe Secondary CTA */}
              <div className="mt-6 border-t border-slate-900 pt-5 flex items-center justify-between gap-4">
                <span className="font-sans text-[11px] text-slate-500 leading-normal">
                  Want to see this feedback loop update in real-time under interactive variables?
                </span>
                <button
                  type="button"
                  onClick={() => setActiveTab('simulator')}
                  className="shrink-0 flex items-center gap-1.5 rounded bg-cyan-950/70 py-1.5 px-3 text-xs font-mono font-medium text-cyan-400 border border-cyan-800/40 hover:bg-cyan-900/60 transition-all"
                  id="wireframe-simulator-btn"
                >
                  Go to Simulator
                  <ArrowRight className="h-3 w-3" />
                </button>
              </div>

            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
