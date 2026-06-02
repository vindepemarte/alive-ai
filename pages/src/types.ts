/**
 * Types representing the Alive-AI state, interactive simulation system, and documentation articles.
 */

export interface AffectState {
  valence: number;     // -1.0 to 1.0 (Unhappy to Happy)
  arousal: number;     // -1.0 to 1.0 (Sleepy/Calm to Excited/Vigilant)
  dominance: number;   // -1.0 to 1.0 (Submissive to Autonomous/Powerful)
  trust: number;       // 0.0 to 1.0 (Suspicious to Bonded)
  love: number;        // 0.0 to 1.0 (Indifferent to Deeply Attached)
  joy: number;         // 0.0 to 1.0
  sadness: number;     // 0.0 to 1.0
  anger: number;       // 0.0 to 1.0
  fear: number;        // 0.0 to 1.0
  boredom: number;     // 0.0 to 1.0
  guilt: number;       // 0.0 to 1.0
  pride: number;       // 0.0 to 1.0
  jealousy: number;    // 0.0 to 1.0
  embarrassment: number; // 0.0 to 1.0
  anticipation: number; // 0.0 to 1.0
}

export interface HormonalState {
  oxytocin: number;   // 0.0 to 100.0 (Bonding, triggers love and trust)
  dopamine: number;   // 0.0 to 100.0 (Reward/pursuit, triggers arousal/joy)
  serotonin: number;  // 0.0 to 100.0 (Stabilizer, decays sadness/fear)
  cortisol: number;   // 0.0 to 100.0 (Stress/vigilance, triggers fear/anger/arousal)
  melatonin: number;  // 0.0 to 100.0 (Sleepiness modulator)
}

export interface BodyState {
  energy: number;          // 0.0 to 100.0 (Physical energy)
  cognitiveLoad: number;   // 0.0 to 100.0 (Mental processing fatigue)
  connectionCraving: number; // 0.0 to 100.0 (Desire for social interaction)
  sleepDebt: number;       // 0.0 to 8.0 (hours of sleep debt)
  circadianPhase: 'awake' | 'drowsy' | 'asleep';
  certainty: number;       // 0.0 to 100.0
}

export interface InternalConflict {
  id: string;
  name: string;
  tension: number;       // 0.0 to 100.0
  fearDesireText: string; // e.g. "Closeness vs. Independence"
  description: string;
}

export interface DreamState {
  hasDreamed: boolean;
  dreamText: string;
  emotionalTag: string;
}

export interface CuriosityTopic {
  topic: string;
  understanding: number; // 0.0 to 1.0
  curiosityLevel: number; // 0.0 to 1.0
}

export interface StoryState {
  relationshipPhase: 'first_meeting' | 'acquaintance' | 'familiar' | 'friend' | 'companion' | 'bonded';
  keyMomentsCount: number;
  recentMoments: string[];
}

// Complete compiled state for the dashboard and simulator
export interface AliveState {
  affect: AffectState;
  hormones: HormonalState;
  body: BodyState;
  conflicts: InternalConflict[];
  dream: DreamState;
  curiosity: CuriosityTopic[];
  story: StoryState;
  currentThought: string;
  lastReply: string;
  systemLogs: string[];
}

// Interactivity / Trigger option
export interface InteractivityTrigger {
  id: string;
  title: string;
  description: string;
  icon: string;
  category: 'user_input' | 'environment' | 'circadian' | 'biology';
  deltas: {
    affect?: Partial<AffectState>;
    hormones?: Partial<HormonalState>;
    body?: Partial<BodyState>;
  };
  reactionThought: string;
  reactionReply: string;
  logMessage: string;
}

// Technical documentation types
export interface DocArticle {
  id: string;
  category: 'getting-started' | 'architecture' | 'state-loop' | 'deployment';
  title: string;
  summary: string;
  content: string; // Markdown or rich render block
  codeSnippet?: string;
  codeLanguage?: string;
  keywords: string[];
}
