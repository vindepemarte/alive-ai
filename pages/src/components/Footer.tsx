import { Github, CloudLightning, Package } from 'lucide-react';
import { motion } from 'motion/react';

interface FooterProps {
  setActiveTab: (tab: string) => void;
}

export default function Footer({ setActiveTab }: FooterProps) {
  // Navigation links
  const links = [
    { label: 'Platform Home', tab: 'home' },
    { label: 'Interactive Simulator', tab: 'simulator' },
    { label: 'Technical Manuals', tab: 'docs' },
  ];

  const socialLinks = [
    { icon: Github, href: 'https://github.com/vindepemarte/alive-ai', label: 'GitHub Repo' },
    { icon: Package, href: 'https://www.npmjs.com/package/alive-ai', label: 'npm Package' },
  ];

  return (
    <footer className="mt-20 border-t border-slate-900 bg-slate-950/40 relative z-10 py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
          
          {/* Brand left side */}
          <div className="md:col-span-4 space-y-4">
            <div className="flex items-center gap-2">
              <img src="./assets/alive-ai-512.png" alt="" className="h-9 w-9 object-contain" />
              <span className="font-sans text-lg font-black text-white tracking-tight">
                Alive<span className="bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent">-AI</span>
              </span>
              <span className="inline-flex items-center gap-1 rounded bg-emerald-950/60 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-400 border border-emerald-800/40 tracking-wider">
                BETA_VER_1.8
              </span>
            </div>
            
            <p className="font-sans text-xs text-slate-400 max-w-sm leading-relaxed font-normal">
              An open-source interactive research experiment introducing simulated affect, circadian pressure metrics, and biological hormone parameters back into continuous AI context pipelines.
            </p>

            <span className="block font-mono text-[10px] text-slate-500">
              MIT License &copy; {new Date().getFullYear()} vindepemarte.
            </span>
          </div>

          {/* Quick Shortcuts */}
          <div className="md:col-span-4 space-y-3">
            <h4 className="font-mono text-[10px] font-bold text-slate-500 uppercase tracking-widest">Platform Shortcuts</h4>
            <div className="flex flex-col gap-2">
              {links.map((link, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    setActiveTab(link.tab);
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  className="self-start text-left font-sans text-xs text-slate-400 hover:text-cyan-400 transition-colors focus:outline-none focus:underline"
                  id={`footer-shortcut-${link.tab}`}
                >
                  {link.label}
                </button>
              ))}
            </div>
          </div>

          {/* Social connections */}
          <div className="md:col-span-4 space-y-3.5">
            <h4 className="font-mono text-[10px] font-bold text-slate-500 uppercase tracking-widest">Nervous Connections</h4>
            <p className="font-sans text-xs text-slate-400 font-normal leading-normal">
              Contribute to the research, inspect core Python modules, or install the latest public npm package.
            </p>
            
            {/* Social icons row */}
            <div className="flex items-center gap-3">
              {socialLinks.map((social, i) => {
                const IconComponent = social.icon;
                return (
                  <a
                    key={i}
                    href={social.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-900 bg-slate-900/30 text-slate-400 hover:border-slate-800 hover:text-white hover:bg-slate-900/60 transition-all cursor-pointer"
                    title={social.label}
                    aria-label={social.label}
                    id={`footer-social-${i}`}
                  >
                    <IconComponent className="h-4 w-4" />
                  </a>
                );
              })}
            </div>

            <div className="flex items-center gap-1.5 font-mono text-[10px] text-slate-600 uppercase tracking-wider">
              <CloudLightning className="h-3 w-3 text-cyan-400" />
              <span>GIVE YOUR AI A REVOLUTIONARY HEART</span>
            </div>
          </div>

        </div>
      </div>
    </footer>
  );
}
