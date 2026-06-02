import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Search, BookOpen, Terminal, Check, Copy, ChevronRight, Slash, 
  Settings, FolderKanban, ShieldCheck, HeartPulse
} from 'lucide-react';
import { DOC_ARTICLES } from '../data/docs';
import { DocArticle } from '../types';

export default function DocsSection() {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [activeArticle, setActiveArticle] = useState<DocArticle>(DOC_ARTICLES[0]);
  const [copiedCode, setCopiedCode] = useState<boolean>(false);

  // Categories definitions list
  const categories = [
    { id: 'all', label: 'All Guides', icon: BookOpen },
    { id: 'getting-started', label: 'Getting Started', icon: ChevronRight },
    { id: 'architecture', label: 'Nervous Systems', icon: HeartPulse },
    { id: 'state-loop', label: 'Background Loops', icon: Terminal },
    { id: 'deployment', label: 'WebUI & Deploy', icon: Settings },
  ];

  // Filtering based on active category and query string
  const filteredArticles = useMemo(() => {
    return DOC_ARTICLES.filter((article) => {
      const matchesCategory = selectedCategory === 'all' || article.category === selectedCategory;
      const q = searchQuery.toLowerCase().trim();
      if (!q) return matchesCategory;

      const matchesSearch = 
        article.title.toLowerCase().includes(q) ||
        article.summary.toLowerCase().includes(q) ||
        article.content.toLowerCase().includes(q) ||
        article.keywords.some(k => k.toLowerCase().includes(q));

      return matchesCategory && matchesSearch;
    });
  }, [selectedCategory, searchQuery]);

  // Handle copying code blocks to keyboard clipboard
  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => {
      setCopiedCode(false);
    }, 1800);
  };

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      
      {/* Search Header Suite */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8 border-b border-slate-900 pb-6">
        <div>
          <h2 className="font-sans text-2xl font-black text-white sm:text-3xl flex items-center gap-2.5">
            <BookOpen className="h-7 w-7 text-cyan-400" />
            Technical Documentation Hub
          </h2>
          <p className="mt-1.5 font-sans text-xs sm:text-sm text-slate-400">
            Search developer manuals, command catalogs, state machine details, and somatic chemical definitions.
          </p>
        </div>

        {/* Dynamic Search Bar */}
        <div className="relative w-full md:w-80">
          <input
            type="text"
            placeholder="Search docs (e.g. sleep debt)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 text-white rounded-lg border border-slate-900 pl-10 pr-4 py-2 font-sans text-sm focus:border-cyan-500/70 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 transition-all font-medium"
            id="docs-search-input"
          />
          <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-500" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* LEFT INDEX COLUMN: Navigation Lists */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Categories Tab Selectors */}
          <div className="rounded-xl border border-slate-900 bg-slate-950/40 p-4 scrollbar-none flex flex-row lg:flex-col gap-2 overflow-x-auto lg:overflow-x-visible">
            {categories.map((cat) => {
              const Icon = cat.icon;
              const isSelected = selectedCategory === cat.id;

              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => {
                    setSelectedCategory(cat.id);
                    // Reset selected active if it falls out of search
                    const matches = DOC_ARTICLES.filter(a => cat.id === 'all' || a.category === cat.id);
                    if (matches.length > 0) setActiveArticle(matches[0]);
                  }}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold font-sans whitespace-nowrap lg:whitespace-normal shrink-0 transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-cyan-950/40 text-cyan-400 border border-cyan-800/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
                  }`}
                  id={`cat-tab-${cat.id}-btn`}
                >
                  <Icon className="h-3.5 w-3.5 shrink-0" />
                  {cat.label}
                </button>
              );
            })}
          </div>

          {/* Article Matching Selection Index */}
          <div className="rounded-xl border border-slate-900 bg-slate-950/40 p-4">
            <h3 className="font-sans text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3 px-1.5 flex items-center justify-between">
              <span>Matching Manuals ({filteredArticles.length})</span>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </h3>

            {filteredArticles.length === 0 ? (
              <div className="text-center py-6 font-sans text-xs text-slate-500 italic">
                No matching topics found for "{searchQuery}"
              </div>
            ) : (
              <div className="space-y-1">
                {filteredArticles.map((article) => {
                  const isActive = activeArticle.id === article.id;
                  return (
                    <button
                      key={article.id}
                      type="button"
                      onClick={() => setActiveArticle(article)}
                      className={`w-full flex items-center justify-between rounded-lg p-2.5 text-left transition-all group cursor-pointer ${
                        isActive
                          ? 'bg-slate-900 text-white font-medium'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
                      }`}
                      id={`article-btn-${article.id}`}
                    >
                      <div className="truncate pr-2">
                        <h4 className="font-sans text-xs font-bold truncate group-hover:text-cyan-300 transition-colors">
                          {article.title}
                        </h4>
                        <p className="font-sans text-[10px] text-slate-500 mt-0.5 truncate leading-tight">
                          {article.summary}
                        </p>
                      </div>
                      <ChevronRight className={`h-3.5 w-3.5 shrink-0 text-slate-600 transition-transform ${
                        isActive ? 'text-cyan-400 translate-x-0.5' : 'group-hover:translate-x-0.5'
                      }`} />
                    </button>
                  );
                })}
              </div>
            )}
          </div>

        </div>

        {/* RIGHT ZONE: Documentation Terminal Viewer */}
        <div className="lg:col-span-8 rounded-2xl border border-slate-900 bg-slate-950/40 p-6 sm:p-8 backdrop-blur-sm shadow-2xl relative min-h-[500px]">
          <div className="absolute top-4 right-4 flex items-center gap-1.5 font-mono text-[9px] text-slate-600 select-none">
            <FolderKanban className="h-3 w-3" />
            V1.8.4_DOC_MODULE
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={activeArticle.id}
              initial={{ opacity: 0, x: 5 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -5 }}
              transition={{ duration: 0.18 }}
              className="space-y-6"
            >
              {/* Category Breadcrumbs */}
              <div className="flex items-center gap-1.5 font-mono text-[9px] font-bold text-slate-500 tracking-wider">
                <span className="uppercase">{activeArticle.category}</span>
                <Slash className="h-2.5 w-2.5 opacity-50 text-slate-700" />
                <span className="text-cyan-400">INDEX_{activeArticle.id.toUpperCase()}</span>
              </div>

              {/* Title Header */}
              <div>
                <h1 className="font-sans text-xl sm:text-2xl font-black text-white tracking-tight">
                  {activeArticle.title}
                </h1>
                <p className="mt-2 font-sans text-xs sm:text-sm text-slate-400 font-normal leading-relaxed">
                  {activeArticle.summary}
                </p>
              </div>

              {/* Main Explanatory Content block (Simulating beautiful formatted rich text) */}
              <div 
                className="font-sans text-xs sm:text-sm text-slate-300 leading-relaxed font-normal space-y-4 pt-4 border-t border-slate-900"
                id="doc-article-details"
              >
                {/* Custom renderer reflecting README values precisely */}
                {activeArticle.content.split('\n\n').map((paragraph, index) => {
                  if (paragraph.startsWith('### ')) {
                    return (
                      <h3 key={index} className="font-sans text-base font-bold text-white mt-6 mb-2">
                        {paragraph.replace('### ', '')}
                      </h3>
                    );
                  }
                  if (paragraph.startsWith('* ')) {
                    return (
                      <ul key={index} className="space-y-1.5 list-disc pl-5 mt-2">
                        {paragraph.split('\n').map((li, i) => (
                          <li key={i} className="leading-relaxed">
                            {li.replace('* ', '')}
                          </li>
                        ))}
                      </ul>
                    );
                  }
                  if (paragraph.startsWith('> ')) {
                    return (
                      <blockquote key={index} className="border-l-2 border-cyan-500 bg-cyan-950/10 p-3.5 rounded-r font-sans text-xs italic text-slate-300 leading-relaxed">
                        {paragraph.replace('> ', '')}
                      </blockquote>
                    );
                  }
                  return (
                    <p key={index} className="leading-relaxed paragraph-doc font-normal">
                      {paragraph}
                    </p>
                  );
                })}
              </div>

              {/* Code Snippets Section */}
              {activeArticle.codeSnippet && (
                <div className="mt-8 rounded-xl border border-slate-900 bg-slate-950 overflow-hidden shadow-inner font-mono text-xs relative">
                  <div className="flex items-center justify-between border-b border-slate-900 px-4 py-2.5 bg-slate-900/40 select-none">
                    <span className="text-[10px] text-slate-500 font-bold tracking-widest uppercase flex items-center gap-1.5">
                      <Terminal className="h-3.5 w-3.5 text-cyan-400" />
                      SOURCE_FILE.{activeArticle.codeLanguage === 'bash' ? 'sh' : 'ts'}
                    </span>
                    
                    {/* Copy Button */}
                    <button
                      type="button"
                      onClick={() => handleCopyCode(activeArticle.codeSnippet || '')}
                      className="flex items-center gap-1 text-[10px] font-mono text-slate-500 hover:text-white transition-colors cursor-pointer"
                      id="copy-code-btn"
                    >
                      {copiedCode ? (
                        <>
                          <Check className="h-3 w-3 text-emerald-400" />
                          <span className="text-emerald-400">COPIED</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3" />
                          <span>COPY CODE</span>
                        </>
                      )}
                    </button>
                  </div>
                  
                  <pre className="p-4 overflow-x-auto text-[11px] text-slate-300 leading-relaxed font-mono">
                    <code>{activeArticle.codeSnippet}</code>
                  </pre>
                </div>
              )}

              {/* Authoritative Badge footer inside article */}
              <div className="mt-8 pt-6 border-t border-slate-900 flex items-center gap-2 text-[10px] font-mono text-slate-500">
                <ShieldCheck className="h-4 w-4 text-cyan-400" />
                <span>CONFIRMED AND VERIFIED ON ALIVE-AI CORE RUNTIME DEPLOYMENTS</span>
              </div>

            </motion.div>
          </AnimatePresence>

        </div>

      </div>
    </div>
  );
}
