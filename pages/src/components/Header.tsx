import { motion } from 'motion/react';
import { Github, Cpu, FileText, Activity } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export default function Header({ activeTab, setActiveTab }: HeaderProps) {
  // Navigation tabs
  const navTabs = [
    { id: 'home', label: 'Home', icon: Cpu },
    { id: 'simulator', label: 'Nervous Simulator', icon: Activity },
    { id: 'docs', label: 'Documentation', icon: FileText },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-900 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        
        {/* Logo and Brand */}
        <div className="flex items-center gap-3">
          <button 
            type="button"
            onClick={() => setActiveTab('home')} 
            className="group flex items-center gap-2.5 focus:outline-none"
            id="header-logo-btn"
          >
            <div className="relative flex h-11 w-11 items-center justify-center">
              <motion.div 
                className="absolute inset-0 rounded-full bg-cyan-500/20 blur-md"
                animate={{
                  scale: [1, 1.2, 1],
                  opacity: [0.5, 0.8, 0.5]
                }}
                transition={{
                  duration: 2.5,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              />
              <img
                src="./assets/alive-ai-512.png"
                alt="Alive-AI official logo"
                className="relative h-10 w-10 object-contain transition-transform duration-300 group-hover:scale-105"
                id="header-logo-img"
              />
            </div>
            
            {/* Text Title with Brand Color Extraction */}
            <div className="flex flex-col items-start leading-none">
              <span className="font-sans text-lg font-bold tracking-tight text-white sm:text-xl">
                Alive<span className="bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent">-AI</span>
              </span>
              <span className="hidden font-mono text-[9px] text-slate-500 sm:block">AFFECTIVE RUNTIME</span>
            </div>
          </button>
          
          {/* Green Beta Badge */}
          <div className="ml-1 items-center">
            <span className="inline-flex items-center gap-1 rounded bg-emerald-950/60 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-800/40 tracking-wider">
              <span className="h-1 w-1 rounded-full bg-emerald-400 animate-pulse" />
              BETA
            </span>
          </div>
        </div>

        {/* Dashboard Navigation */}
        <nav className="flex items-center gap-1 sm:gap-2">
          {navTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`relative flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 font-sans text-xs font-semibold tracking-wide transition-all sm:text-sm focus:outline-none focus:ring-1 focus:ring-cyan-500/30 ${
                  isActive 
                    ? 'text-cyan-400 font-medium' 
                    : 'text-slate-400 hover:text-white hover:bg-slate-900/40'
                }`}
                id={`nav-${tab.id}-btn`}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{tab.label}</span>
                {isActive && (
                  <motion.div 
                    layoutId="activeBubble"
                    className="absolute inset-0 -z-10 rounded-lg bg-cyan-950/40 border border-cyan-500/20"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                  />
                )}
              </button>
            );
          })}
        </nav>

        {/* Third-Party Repository Links */}
        <div className="flex items-center gap-4">
          <a
            href="https://github.com/vindepemarte/alive-ai"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-700 hover:text-white transition-all font-mono"
            title="View Official Github"
            id="github-link-btn"
          >
            <Github className="h-3.5 w-3.5" />
            <span className="hidden md:inline">vindepemarte / alive-ai</span>
            <span className="md:hidden">GitHub</span>
          </a>
        </div>

      </div>
    </header>
  );
}
