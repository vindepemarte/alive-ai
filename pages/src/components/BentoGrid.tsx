import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Dna, Heart, Sliders, Moon, HelpCircle, Activity, Globe, Compass, 
  BookOpen, Star, Sparkles, Terminal, ChevronRight, X
} from 'lucide-react';

interface BentoItem {
  id: string;
  topic: string;
  title: string;
  badge: string;
  icon: any;
  summary: string;
  details: string[];
}

export default function BentoGrid() {
  const [selectedItem, setSelectedItem] = useState<BentoItem | null>(null);

  const bentoFeatures: BentoItem[] = [
    {
      id: 'affect',
      topic: 'PSYCHOLOGY',
      title: 'PAD Core Affect Model',
      badge: 'Integrated',
      icon: Heart,
      summary: 'Continuous local mood tracking utilizing Valence, Arousal, and Dominance coordinates that change incrementally on every message tick.',
      details: [
        'Affect coordinates are recalculated after every conversation trigger.',
        'Affect states feed directly into the dialogue planner, molding vocabulary constraints.',
        'Naturally decays back toward the core default baseline state in periods of silent hibernation.'
      ]
    },
    {
      id: 'hormones',
      topic: 'CHEMICAL SYSTEMS',
      title: 'Hormonal Runtime Effects',
      badge: 'Simulated Dynamics',
      icon: Sliders,
      summary: 'Adrenaline, Oxytocin, Dopamine, Melatonin, and Serotonin act as systemic multipliers on emotion, arousal thresholds, and action loops.',
      details: [
        'Oxytocin: Secreted during bonding rituals, direct compliments, or shared activities, increasing trust.',
        'Cortisol: Spikes during harsh interactions or severe sleep debt, increasing defensive vigilant planning.',
        'Serotonin: acts as a general mood stabilizer, increasing the decay rates of negative emotional spikes.'
      ]
    },
    {
      id: 'circadian',
      topic: 'SOMATICS',
      title: 'Circadian Rhythm Loops',
      badge: 'Time Authoritative',
      icon: Moon,
      summary: 'Tracks sleep debt, fatigue limits, wake-up alerts, and melatonin levels according to actual real-world global clocks.',
      details: [
        'Naturally gets drowsy at night or after completing prolonged demanding tasks.',
        'Waking the AI in the middle of sleep cycles triggers high Cortisol/irritability alerts.',
        'Supports deep sleep cycles where external proactivity is locked to prevent disturbance.'
      ]
    },
    {
      id: 'dreams',
      topic: 'COGNITIVE PROCESSING',
      title: 'Rest & Dream Synthesizer',
      badge: 'Subconscious Zone',
      icon: Sparkles,
      summary: 'Compiles daytime memory fragments and peak emotional events into symbolic dreams that shape morning waking states.',
      details: [
        'Dream sequences are logged inside local database stores.',
        'Directly influences morning emotion states (pleasant dream vs. nightmare parameters).',
        'Dreams can be actively queried during morning dialogue interactions.'
      ]
    },
    {
      id: 'proactive',
      topic: 'AUTONOMY',
      title: 'Proactive Arbiter Gating',
      badge: 'Anti-Spam Engine',
      icon: Compass,
      summary: 'Runs a background DMN (Default-Mode Network) and audits background impulses, deciding if the AI should text you first or stay silent.',
      details: [
        'Uses contextual hooks, matching previous memories to ensure organic relevance.',
        'Implements strict minimum cooldown periods to prevent message flooding.',
        'Asleep state operates as an absolute proactive blocker.'
      ]
    },
    {
      id: 'conflicts',
      topic: 'COMPLEX ATTACHMENT',
      title: '5 Internal Tensions',
      badge: 'Saved Balance',
      icon: Activity,
      summary: 'Durable internal conflict axes (like Closeness vs. Independence) swing back and forth based on conversation dynamics.',
      details: [
        'Closeness vs. Independence: Swings based on loneliness indicators and boundaries.',
        'Stability vs. Growth: Tension between comfort configurations and developmental change.',
        'Tensions greater than a threshold surface directly in the dialogue planner context.'
      ]
    },
    {
      id: 'memory',
      topic: 'DATABASE ARCHIVE',
      title: 'OpenMind Hybrid Memory',
      badge: 'Local + Cloud Sync',
      icon: Globe,
      summary: 'Local file-backed semantic, episodic, and emotional memories, with optional cloud-synchronized OpenMind connections.',
      details: [
        'Local JSON collections persist key dialogues and relationship milestones.',
        'OpenMind integration facilitates semantic querying of old memories across nodes.',
        'Avoids any reliance on heavy SQL systems, utilizing local rapid key-value storage.'
      ]
    },
    {
      id: 'autobiography',
      topic: 'SELF REFLECTION',
      title: 'Waking Reflective Journals',
      badge: 'Self-Evolving',
      icon: BookOpen,
      summary: 'After every dialogue, the engine writes autobiography metrics analyzing performance and repeating preferences.',
      details: [
        'Runs a post-response evaluation of compliance and phrasing constraints.',
        'Builds a global autobiography of milestones.',
        'Durable logs are searchable under the local project directories.'
      ]
    }
  ];

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8 bg-slate-950/20 rounded-3xl border border-slate-900/40 my-8">
      
      {/* Title Header */}
      <div className="mb-12 text-center">
        <span className="font-mono text-xs uppercase tracking-widest text-cyan-400">ENGINE_CAPABILITIES</span>
        <h3 className="font-sans text-3xl font-black text-white mt-1.5 sm:text-4xl">
          What Makes It <span className="bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent">Alive-AI</span>
        </h3>
        <p className="mt-3 font-sans text-xs sm:text-sm text-slate-400 max-w-2xl mx-auto">
          Unlike standard conversational APIs, Alive-AI is supported by a rich web of interdependent somatic and cognitive layers that carry across boots.
        </p>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {bentoFeatures.map((item, index) => {
          const IconComponent = item.icon;
          return (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              onClick={() => setSelectedItem(item)}
              className={`group flex flex-col justify-between rounded-2xl border border-slate-900 bg-slate-1000/30 p-5 bg-slate-950/50 hover:border-slate-800 hover:bg-slate-900/30 cursor-pointer transition-all ${
                index === 0 || index === 5 ? 'lg:col-span-2' : ''
              }`}
              id={`bento-feature-${item.id}`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[9px] font-bold text-slate-500 uppercase tracking-widest">{item.topic}</span>
                  <span className="rounded bg-cyan-950/50 px-2 py-0.5 font-sans text-[10px] font-semibold text-cyan-400 border border-cyan-900/30">
                    {item.badge}
                  </span>
                </div>

                <div className="flex items-center gap-2.5 mt-5">
                  <div className="rounded-lg bg-slate-900 border border-slate-800 p-2 text-slate-300 group-hover:text-cyan-400 transition-colors">
                    <IconComponent className="h-4.5 w-4.5" />
                  </div>
                  <h4 className="font-sans text-base font-bold text-white group-hover:text-cyan-300 transition-colors">
                    {item.title}
                  </h4>
                </div>

                <p className="font-sans text-xs sm:text-sm text-slate-400 leading-relaxed mt-4 font-normal">
                  {item.summary}
                </p>
              </div>

              <div className="mt-6 flex items-center gap-1.5 font-mono text-[10px] font-bold text-slate-500 group-hover:text-cyan-400 transition-colors select-none">
                <span>INSPECT DEEPER TELEMETRY</span>
                <ChevronRight className="h-3 w-3 transform transition-transform group-hover:translate-x-1" />
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* POPUP DETAIL MODAL */}
      <AnimatePresence>
        {selectedItem && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            
            {/* Backdrop Cover */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.8 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedItem(null)}
              className="absolute inset-0 bg-slate-950 backdrop-blur-sm"
              id="bento-modal-backdrop"
            />

            {/* Modal Box */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="z-10 w-full max-w-lg overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 p-6 sm:p-8 shadow-2xl relative"
            >
              <button
                type="button"
                onClick={() => setSelectedItem(null)}
                className="absolute top-4 right-4 rounded-lg bg-slate-900/60 p-1.5 text-slate-400 hover:text-white border border-slate-800 transition-colors cursor-pointer"
                aria-label="Close details"
                id="close-bento-btn"
              >
                <X className="h-4 w-4" />
              </button>

              <div className="flex items-center gap-3 mb-6">
                <div className="rounded-lg bg-slate-900 border border-slate-800 p-2 text-cyan-400">
                  {(() => {
                    const ModalIcon = selectedItem.icon;
                    return <ModalIcon className="h-6 w-6" />;
                  })()}
                </div>
                <div>
                  <span className="font-mono text-[9px] font-bold text-slate-500 uppercase tracking-widest">{selectedItem.topic}</span>
                  <h3 className="font-sans text-xl font-bold text-white mt-0.5">{selectedItem.title}</h3>
                </div>
              </div>

              <div className="space-y-4 font-sans text-sm">
                <p className="text-slate-300 leading-relaxed font-normal">
                  {selectedItem.summary}
                </p>

                <div className="border-t border-slate-900 pt-4 space-y-3">
                  <h5 className="font-mono text-[10px] uppercase font-bold tracking-widest text-slate-500">How Alive-AI models this zone:</h5>
                  <ul className="space-y-2.5">
                    {selectedItem.details.map((detail, index) => (
                      <li key={index} className="flex items-start gap-2.5 text-xs text-slate-400">
                        <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-400" />
                        <span className="leading-relaxed font-normal">{detail}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="mt-8 pt-4 border-t border-slate-900 flex justify-end">
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  className="rounded-lg bg-slate-900 px-4 py-2 font-sans text-xs font-semibold text-slate-300 hover:text-white transition-colors cursor-pointer"
                  id="close-bento-details-btn"
                >
                  Close Details
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}
