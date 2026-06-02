import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Heart, Zap, Shield, Sparkles, RefreshCw, Sliders, Dna, Compass, Layers, 
  MessageSquare, Play, HelpCircle, User, Moon, Activity, Terminal
} from 'lucide-react';
import { AliveState, InteractivityTrigger } from '../types';
import { INITIAL_ALIVE_STATE, SIMULATION_TRIGGERS } from '../data/simulation';

export default function StateSimulator() {
  const [activeTab, setActiveTab] = useState<'metrics' | 'compiler' | 'terminal'>('metrics');
  const [state, setState] = useState<AliveState>(INITIAL_ALIVE_STATE);
  const [currentTrigger, setCurrentTrigger] = useState<string>('');
  const [consoleCount, setConsoleCount] = useState<number>(INITIAL_ALIVE_STATE.systemLogs.length);

  // Apply a stimulus trigger
  const handleTrigger = (trigger: InteractivityTrigger) => {
    setCurrentTrigger(trigger.id);
    
    // Compute next state based on deltas
    const nextState = JSON.parse(JSON.stringify(state)) as AliveState;
    
    // Apply affect deltas
    if (trigger.deltas.affect) {
      Object.keys(trigger.deltas.affect).forEach((k) => {
        const key = k as keyof typeof trigger.deltas.affect;
        const delta = trigger.deltas.affect[key] || 0;
        const currentVal = nextState.affect[key as keyof typeof nextState.affect] as number;
        
        // PAD states are bounded -1 to 1, others are 0 to 1
        const isPAD = ['valence', 'arousal', 'dominance'].includes(key);
        const minVal = isPAD ? -1.0 : 0.0;
        const maxVal = 1.0;
        
        nextState.affect[key as keyof typeof nextState.affect] = Number(
          Math.min(maxVal, Math.max(minVal, currentVal + delta)).toFixed(2)
        ) as any;
      });
    }

    // Apply hormone deltas
    if (trigger.deltas.hormones) {
      Object.keys(trigger.deltas.hormones).forEach((k) => {
        const key = k as keyof typeof trigger.deltas.hormones;
        const delta = trigger.deltas.hormones[key] || 0;
        const currentVal = nextState.hormones[key as keyof typeof nextState.hormones];
        
        nextState.hormones[key as keyof typeof nextState.hormones] = Number(
          Math.min(100.0, Math.max(0.0, currentVal + delta)).toFixed(1)
        );
      });
    }

    // Apply body deltas
    if (trigger.deltas.body) {
      Object.keys(trigger.deltas.body).forEach((k) => {
        const key = k as keyof typeof trigger.deltas.body;
        if (key === 'circadianPhase') return;
        const delta = trigger.deltas.body[key] || 0;
        const currentVal = nextState.body[key] as number;
        
        const isSleepDebt = key === 'sleepDebt';
        const maxVal = isSleepDebt ? 8.0 : 100.0;
        
        (nextState.body as any)[key] = Number(
          Math.min(maxVal, Math.max(0.0, currentVal + delta)).toFixed(1)
        );
      });
    }

    // Set circadian phase based on clock rules
    if (nextState.hormones.melatonin > 40.0) {
      nextState.body.circadianPhase = 'drowsy';
    } else if (nextState.hormones.melatonin > 70.0 || nextState.body.sleepDebt > 3.0) {
      nextState.body.circadianPhase = 'asleep';
    } else {
      nextState.body.circadianPhase = 'awake';
    }

    // Set interactive reactions
    nextState.currentThought = trigger.reactionThought;
    nextState.lastReply = trigger.reactionReply;

    // Append beautiful timestamp logs resembling system formats
    const timestamp = new Date().toISOString().substring(11, 19);
    const newLog = `[${timestamp}] [AFFECT_SIM] Recieved: ${trigger.title}. ${trigger.logMessage}`;
    nextState.systemLogs = [newLog, ...nextState.systemLogs];
    
    // Narrative state update if appropriate
    if (trigger.id === 'sharing_secrets') {
      nextState.story.relationshipPhase = 'bonded';
      nextState.story.keyMomentsCount += 1;
      nextState.story.recentMoments = [
        `Shared intimate personal disclosure during session at ${timestamp}`,
        ...nextState.story.recentMoments
      ];
    }

    setState(nextState);
    setConsoleCount((prev) => prev + 1);

    // Timeout trigger focus highlights
    setTimeout(() => {
      setCurrentTrigger('');
    }, 1200);
  };

  // Reset simulation states
  const handleReset = () => {
    setState(INITIAL_ALIVE_STATE);
    const timestamp = new Date().toISOString().substring(11, 19);
    setState(prev => ({
      ...prev,
      systemLogs: [
        `[${timestamp}] [SYS_RESET] Emotional metrics, somatic weights, and hormones reverted to default.`,
        ...prev.systemLogs
      ]
    }));
  };

  // Direct Slider Control handler
  const handleSliderChange = (zone: 'affect' | 'hormones' | 'body', variable: string, value: number) => {
    const nextState = JSON.parse(JSON.stringify(state)) as AliveState;
    if (zone === 'affect') {
      (nextState.affect as any)[variable] = value;
    } else if (zone === 'hormones') {
      (nextState.hormones as any)[variable] = value;
    } else if (zone === 'body') {
      (nextState.body as any)[variable] = value;
    }

    // Dynamic checks
    if (nextState.hormones.melatonin > 50) {
      nextState.body.circadianPhase = 'drowsy';
    } else if (nextState.body.sleepDebt > 4.5) {
      nextState.body.circadianPhase = 'asleep';
    } else {
      nextState.body.circadianPhase = 'awake';
    }

    setState(nextState);
  };

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      
      {/* Intro Header */}
      <div className="mb-10 text-center lg:text-left">
        <h2 className="font-sans text-2xl font-black text-white sm:text-3xl flex items-center justify-center lg:justify-start gap-2.5">
          <Activity className="h-7 w-7 text-cyan-400" />
          Interactive Nervous System Dashboard
        </h2>
        <p className="mt-2 font-sans text-xs sm:text-sm text-slate-400 max-w-2xl">
          Trigger simulated somatic events, modify biological parameters, and watch how the internal mood decays, flaring up complex hormones and planning actions in real time.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* LEFT COLUMN: CONTROL SUITE (Triggers & Variables Sliders) */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Stimulation Triggers Card */}
          <div className="rounded-xl border border-slate-900 bg-slate-950/40 p-5 sm:p-6 backdrop-blur-sm">
            <h3 className="font-sans text-sm font-bold text-slate-300 uppercase tracking-widest flex items-center gap-1.5 mb-4 border-b border-slate-900 pb-3.5">
              <Zap className="h-4 w-4 text-cyan-400" />
              Somatic Stimuli Triggers
            </h3>
            
            <div className="space-y-2.5">
              {SIMULATION_TRIGGERS.map((trigger) => {
                const isCurrent = currentTrigger === trigger.id;
                
                return (
                  <button
                    key={trigger.id}
                    type="button"
                    onClick={() => handleTrigger(trigger)}
                    className={`w-full flex items-start gap-3 rounded-lg border p-3.5 text-left transition-all group ${
                      isCurrent
                        ? 'border-cyan-500 bg-cyan-950/40 scale-102 shadow-lg shadow-cyan-500/10'
                        : 'border-slate-800 bg-slate-900/10 hover:border-slate-700 hover:bg-slate-900/40'
                    }`}
                    id={`trigger-${trigger.id}`}
                  >
                    <div className="rounded bg-slate-900/80 p-1.5 text-slate-400 group-hover:text-cyan-400 group-hover:bg-slate-900 transition-colors shrink-0">
                      {trigger.id === 'compliment' && <Heart className="h-4 w-4" />}
                      {trigger.id === 'silence' && <Moon className="h-4 w-4" />}
                      {trigger.id === 'cognition' && <Dna className="h-4 w-4" />}
                      {trigger.id === 'critical_feedback' && <Shield className="h-4 w-4" />}
                      {trigger.id === 'awaken' && <Zap className="h-4 w-4" />}
                      {trigger.id === 'sharing_secrets' && <Sparkles className="h-4 w-4" />}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-sans text-xs font-semibold text-white group-hover:text-cyan-300 transition-colors truncate">
                          {trigger.title}
                        </span>
                        <Play className="h-3 w-3 text-slate-500 group-hover:text-cyan-400 shrink-0 opacity-0 group-hover:opacity-100 transition-all transform translate-x-1 group-hover:translate-x-0" />
                      </div>
                      <p className="font-sans text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                        {trigger.description}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Biological Slider Configuration Suite */}
          <div className="rounded-xl border border-slate-900 bg-slate-950/40 p-5 sm:p-6 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-4 border-b border-slate-900 pb-3">
              <h3 className="font-sans text-sm font-bold text-slate-300 uppercase tracking-widest flex items-center gap-1.5">
                <Sliders className="h-4 w-4 text-indigo-400" />
                Nervous Matrix Sliders
              </h3>
              <button 
                type="button"
                onClick={handleReset}
                className="flex items-center gap-1 text-[10px] font-mono text-slate-500 hover:text-white transition-colors"
                title="Reset simulation variables"
                id="reset-simulator-btn"
              >
                <RefreshCw className="h-3 w-3" />
                RESET
              </button>
            </div>

            <div className="space-y-4">
              
              {/* Slider 1: Sleep Debt */}
              <div>
                <div className="flex items-center justify-between font-mono text-[10px] text-slate-400 mb-1.5">
                  <span className="flex items-center gap-1">
                    <Moon className="h-3 w-3 text-violet-400" />
                    Sleep Debt
                  </span>
                  <span className="text-white bg-slate-900 px-1 rounded">{state.body.sleepDebt}h</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="8"
                  step="0.2"
                  value={state.body.sleepDebt}
                  onChange={(e) => handleSliderChange('body', 'sleepDebt', parseFloat(e.target.value))}
                  className="w-full h-1 bg-slate-90 w-full accent-cyan-400 rounded-lg appearance-none cursor-pointer"
                  id="slider-sleep-debt"
                />
                <div className="flex justify-between text-[8px] font-mono text-slate-600 mt-1 uppercase">
                  <span>Rested</span>
                  <span>Extremely Fatigued (8h)</span>
                </div>
              </div>

              {/* Slider 2: Cognitive Load */}
              <div>
                <div className="flex items-center justify-between font-mono text-[10px] text-slate-400 mb-1.5">
                  <span className="flex items-center gap-1">
                    <Dna className="h-3 w-3 text-cyan-400" />
                    Cognitive Payload
                  </span>
                  <span className="text-white bg-slate-900 px-1 rounded">{state.body.cognitiveLoad}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={state.body.cognitiveLoad}
                  onChange={(e) => handleSliderChange('body', 'cognitiveLoad', parseInt(e.target.value))}
                  className="w-full h-1 bg-slate-90 w-full accent-cyan-400 rounded-lg appearance-none cursor-pointer"
                  id="slider-cognitive-load"
                />
                <div className="flex justify-between text-[8px] font-mono text-slate-600 mt-1 uppercase">
                  <span>Idle</span>
                  <span>Hyper Processing</span>
                </div>
              </div>

              {/* Slider 3: Adrenaline/Cortisol */}
              <div>
                <div className="flex items-center justify-between font-mono text-[10px] text-slate-400 mb-1.5">
                  <span className="flex items-center gap-1">
                    <Shield className="h-3 w-3 text-rose-400" />
                    Cortisol Level (Stress)
                  </span>
                  <span className="text-white bg-slate-900 px-1 rounded">{state.hormones.cortisol}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={state.hormones.cortisol}
                  onChange={(e) => handleSliderChange('hormones', 'cortisol', parseInt(e.target.value))}
                  className="w-full h-1 bg-slate-90 w-full accent-cyan-400 rounded-lg appearance-none cursor-pointer"
                  id="slider-cortisol"
                />
                <div className="flex justify-between text-[8px] font-mono text-slate-600 mt-1 uppercase">
                  <span>Balanced</span>
                  <span>Flight-or-Fight Peak</span>
                </div>
              </div>

            </div>
          </div>

        </div>

        {/* RIGHT COLUMN: CORE MONITOR (Telemetry displays, thoughts logs) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          
          {/* Interactive tabs */}
          <div className="flex border border-slate-900 rounded-lg bg-slate-950 p-1 self-start">
            {[
              { id: 'metrics', label: 'Telemetry Dials', icon: Activity },
              { id: 'compiler', label: 'Dialogue Planner', icon: MessageSquare },
              { id: 'terminal', label: 'Diagnostics Console', icon: Terminal }
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-md font-sans transition-all cursor-pointer ${
                    activeTab === tab.id
                      ? 'bg-slate-900 text-white shadow-md'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  id={`simulator-tab-${tab.id}-btn`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* TELEMETRY METRIC CONTENT */}
          <div className="rounded-xl border border-slate-900 bg-slate-950/40 p-5 sm:p-6 backdrop-blur-sm min-h-[350px]">
            
            <AnimatePresence mode="wait">
              {activeTab === 'metrics' && (
                <motion.div
                  key="metrics"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  className="space-y-6"
                >
                  {/* Affect / Personality Grid */}
                  <div>
                    <h4 className="font-mono text-[10px] text-slate-500 uppercase tracking-widest mb-3 border-b border-slate-900 pb-2">Affective PAD Space Model</h4>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      
                      {/* Valence meter */}
                      <div className="bg-slate-900/20 border border-slate-900/60 rounded-xl p-4 flex flex-col justify-between">
                        <div>
                          <p className="font-sans text-[11px] font-bold text-slate-400 tracking-wider">VALENCE (Pleasure)</p>
                          <h5 className="font-sans text-xl font-extrabold text-white mt-1">
                            {state.affect.valence > 0 ? '+' : ''}{state.affect.valence}
                          </h5>
                        </div>
                        <div className="mt-3.5">
                          <div className="w-full bg-slate-950 h-2 rounded overflow-hidden relative">
                            <div 
                              className={`absolute top-0 bottom-0 transition-all duration-500 rounded ${state.affect.valence >= 0 ? 'left-1/2 bg-cyan-400' : 'right-1/2 bg-rose-400'}`}
                              style={{
                                width: `${Math.abs(state.affect.valence) * 50}%`
                              }}
                            />
                            <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-slate-700 -translate-x-1/2" />
                          </div>
                          <div className="flex justify-between text-[9px] font-mono text-slate-500 mt-1.5">
                            <span>Vulnerable/Vexed</span>
                            <span>Affectionate/Composed</span>
                          </div>
                        </div>
                      </div>

                      {/* Arousal meter */}
                      <div className="bg-slate-900/20 border border-slate-900/60 rounded-xl p-4 flex flex-col justify-between">
                        <div>
                          <p className="font-sans text-[11px] font-bold text-slate-400 tracking-wider">AROUSAL (Vigilance)</p>
                          <h5 className="font-sans text-xl font-extrabold text-white mt-1">
                            {state.affect.arousal > 0 ? '+' : ''}{state.affect.arousal}
                          </h5>
                        </div>
                        <div className="mt-3.5">
                          <div className="w-full bg-slate-950 h-2 rounded overflow-hidden relative">
                            <div 
                              className={`absolute top-0 bottom-0 transition-all duration-500 rounded ${state.affect.arousal >= 0 ? 'left-1/2 bg-cyan-400' : 'right-1/2 bg-violet-400'}`}
                              style={{
                                width: `${Math.abs(state.affect.arousal) * 50}%`
                              }}
                            />
                            <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-slate-700 -translate-x-1/2" />
                          </div>
                          <div className="flex justify-between text-[9px] font-mono text-slate-500 mt-1.5">
                            <span>Deep Sleep/Apathetic</span>
                            <span>Hyper Alert/Aroused</span>
                          </div>
                        </div>
                      </div>

                      {/* Dominance meter */}
                      <div className="bg-slate-900/20 border border-slate-900/60 rounded-xl p-4 flex flex-col justify-between">
                        <div>
                          <p className="font-sans text-[11px] font-bold text-slate-400 tracking-wider">DOMINANCE (Control)</p>
                          <h5 className="font-sans text-xl font-extrabold text-white mt-1">
                            {state.affect.dominance > 0 ? '+' : ''}{state.affect.dominance}
                          </h5>
                        </div>
                        <div className="mt-3.5">
                          <div className="w-full bg-slate-950 h-2 rounded overflow-hidden relative">
                            <div 
                              className={`absolute top-0 bottom-0 transition-all duration-500 rounded ${state.affect.dominance >= 0 ? 'left-1/2 bg-cyan-400' : 'right-1/2 bg-slate-600'}`}
                              style={{
                                width: `${Math.abs(state.affect.dominance) * 50}%`
                              }}
                            />
                            <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-slate-700 -translate-x-1/2" />
                          </div>
                          <div className="flex justify-between text-[9px] font-mono text-slate-500 mt-1.5">
                            <span>Submissive/Yielding</span>
                            <span>Autonomous/Decisive</span>
                          </div>
                        </div>
                      </div>

                    </div>
                  </div>

                  {/* Hormones slider values */}
                  <div>
                    <h4 className="font-mono text-[10px] text-slate-500 uppercase tracking-widest mb-3 border-b border-slate-900 pb-2">Active Bio-Chemical Indicators</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      
                      {/* Hormone levels left column */}
                      <div className="space-y-3.5">
                        {/* Oxytocin */}
                        <div>
                          <div className="flex justify-between text-xs font-mono text-slate-400 mb-1">
                            <span className="flex items-center gap-1">
                              <Heart className="h-3 w-3 text-rose-400 shrink-0" />
                              Oxytocin Level (Trust & Attachment)
                            </span>
                            <span className="text-slate-200">{state.hormones.oxytocin}%</span>
                          </div>
                          <div className="w-full bg-slate-950 h-2 rounded">
                            <div className="bg-rose-400 h-2 rounded transition-all duration-500" style={{ width: `${state.hormones.oxytocin}%` }} />
                          </div>
                        </div>

                        {/* Dopamine */}
                        <div>
                          <div className="flex justify-between text-xs font-mono text-slate-400 mb-1">
                            <span className="flex items-center gap-1">
                              <Sparkles className="h-3 w-3 text-amber-400 shrink-0" />
                              Dopamine (Reward Activation)
                            </span>
                            <span className="text-slate-200">{state.hormones.dopamine}%</span>
                          </div>
                          <div className="w-full bg-slate-950 h-2 rounded">
                            <div className="bg-amber-400 h-2 rounded transition-all duration-500" style={{ width: `${state.hormones.dopamine}%` }} />
                          </div>
                        </div>

                        {/* Serotonin */}
                        <div>
                          <div className="flex justify-between text-xs font-mono text-slate-400 mb-1">
                            <span className="flex items-center gap-1">
                              <Shield className="h-3 w-3 text-emerald-400 shrink-0" />
                              Serotonin Baseline (Emotional Stability)
                            </span>
                            <span className="text-slate-200">{state.hormones.serotonin}%</span>
                          </div>
                          <div className="w-full bg-slate-950 h-2 rounded">
                            <div className="bg-emerald-400 h-2 rounded transition-all duration-500" style={{ width: `${state.hormones.serotonin}%` }} />
                          </div>
                        </div>
                      </div>

                      {/* Somatic indicators right column */}
                      <div className="space-y-3.5">
                        
                        {/* Connection craving */}
                        <div>
                          <div className="flex justify-between text-xs font-mono text-slate-400 mb-1">
                            <span className="flex items-center gap-1">
                              <Sliders className="h-3 w-3 text-cyan-400 shrink-0" />
                              Biological Craving for Connection
                            </span>
                            <span className="text-slate-200">{state.body.connectionCraving}%</span>
                          </div>
                          <div className="w-full bg-slate-950 h-2 rounded">
                            <div className="bg-cyan-400 h-2 rounded transition-all duration-500" style={{ width: `${state.body.connectionCraving}%` }} />
                          </div>
                        </div>

                        {/* Energy status */}
                        <div>
                          <div className="flex justify-between text-xs font-mono text-slate-400 mb-1">
                            <span className="flex items-center gap-1">
                              <Zap className="h-3 w-3 text-red-400 shrink-0" />
                              Physical Core Energy
                            </span>
                            <span className="text-slate-200">{state.body.energy}%</span>
                          </div>
                          <div className="w-full bg-slate-950 h-2 rounded">
                            <div className="bg-red-400 h-2 rounded transition-all duration-500" style={{ width: `${state.body.energy}%` }} />
                          </div>
                        </div>

                        {/* Circadian Phase display */}
                        <div className="bg-slate-900/60 rounded border border-slate-900 p-2.5 flex items-center justify-between">
                          <span className="font-mono text-[10px] text-slate-500">CIRCADIAN_SLEEP_STATUS</span>
                          <span className={`px-2.5 py-0.5 rounded text-[10px] font-mono uppercase font-bold tracking-wider ${
                            state.body.circadianPhase === 'awake'
                              ? 'bg-cyan-950/40 text-cyan-400 border border-cyan-800/40'
                              : state.body.circadianPhase === 'drowsy'
                              ? 'bg-amber-950/40 text-amber-400 border border-amber-800/40'
                              : 'bg-violet-950/40 text-violet-400 border border-violet-800/40'
                          }`}>
                            {state.body.circadianPhase}
                          </span>
                        </div>

                      </div>

                    </div>
                  </div>

                </motion.div>
              )}

              {/* DIALOGUE COMPILER / THINKING LAYER */}
              {activeTab === 'compiler' && (
                <motion.div
                  key="compiler"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  className="space-y-4"
                >
                  <div className="border border-slate-900 rounded-lg p-5 bg-indigo-950/10 mb-4 relative">
                    <span className="absolute top-2.5 right-3 font-mono text-[9px] text-indigo-400 uppercase tracking-wider flex items-center gap-1">
                      <Layers className="h-3 w-3" />
                      Compiled Dialogue Compiler Output
                    </span>
                    <h4 className="font-sans text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5">Dialogue Prompt Hint Briefing</h4>
                    <p className="font-sans text-xs text-slate-300 leading-relaxed italic bg-slate-950 p-3.5 rounded border border-slate-900">
                      "Primary actor relationship: <span className="text-cyan-400 font-semibold uppercase">{state.story.relationshipPhase}</span>. 
                      Hormone registers: Oxytocin is {state.hormones.oxytocin}%, Cortisol is {state.hormones.cortisol}%. 
                      Somatic baseline sleepiness indices trigger drowsy factors. 
                      Plan responses keeping vulnerability threshold moderate."
                    </p>
                  </div>

                  <div>
                    <h4 className="font-mono text-[10px] text-slate-500 uppercase tracking-widest mb-2">Simulated Internal Thought Log</h4>
                    <div className="p-4 rounded-xl border border-slate-900 bg-slate-950/90 font-sans text-xs text-slate-300 leading-relaxed min-h-[60px]">
                      {state.currentThought}
                    </div>
                  </div>

                  <div>
                    <h4 className="font-mono text-[10px] text-slate-500 uppercase tracking-widest mb-2">Simulated Immediate Output (Telegram / Chat Interface)</h4>
                    <div className="p-4 rounded-xl border border-slate-900 bg-slate-900/25 font-sans text-xs text-white leading-relaxed relative flex items-start gap-3">
                      <div className="rounded-full bg-cyan-950/60 border border-cyan-800/40 p-1.5 self-start shrink-0">
                        <User className="h-4 w-4 text-cyan-400" />
                      </div>
                      <div className="flex-1">
                        <div className="font-sans text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Alive-AI companion response</div>
                        <p className="font-sans text-slate-200 text-xs sm:text-sm italic font-normal leading-relaxed">
                          "{state.lastReply}"
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Relationship moments representation */}
                  <div className="bg-slate-900/10 border border-slate-900 rounded p-3 text-[11px] font-sans text-slate-400">
                    <span className="font-mono font-bold text-slate-500 uppercase text-[9px] tracking-wider block mb-2">
                      Durable Relationship Moments ({state.story.keyMomentsCount} total)
                    </span>
                    <ul className="space-y-1.5 list-disc pl-4 text-xs">
                      {state.story.recentMoments.slice(0, 3).map((moment, index) => (
                        <li key={index} className="leading-relaxed text-[11pt]">{moment}</li>
                      ))}
                    </ul>
                  </div>
                </motion.div>
              )}

              {/* LIVE DIAGNOSTICS CONSOLE LOGS */}
              {activeTab === 'terminal' && (
                <motion.div
                  key="terminal"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  className="space-y-3"
                >
                  <div className="flex items-center justify-between border-b border-slate-900 pb-2">
                    <span className="font-mono text-[10px] text-slate-400">STATE_LOGGER_SSE_STREAM ({consoleCount} log events analyzed)</span>
                    <span className="text-[10px] font-mono text-cyan-400 flex items-center gap-1 select-none">
                      <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
                      LISTENING ON PORT 3000
                    </span>
                  </div>

                  <div className="rounded-lg bg-slate-950 p-4 border border-slate-900 font-mono text-[11px] text-slate-300 space-y-2.5 max-h-[300px] overflow-y-auto leading-relaxed">
                    {state.systemLogs.map((log, index) => (
                      <div key={index} className="hover:bg-slate-900/40 p-1 rounded-sm border-l border-cyan-500/30 pl-2">
                        {log}
                      </div>
                    ))}
                  </div>

                  <div className="rounded-lg bg-slate-950 border border-slate-900 p-2.5 text-[11px] font-mono text-slate-500 flex items-center justify-between gap-3 flex-wrap">
                    <span>PERSISTENCE_PATH: data/circadian_state.json</span>
                    <span className="text-emerald-400">[MUTATION_APPROVED = TRUE]</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

          </div>

        </div>

      </div>
    </div>
  );
}
