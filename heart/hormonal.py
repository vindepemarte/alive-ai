"""
Heart: Hormonal Modulation Matrix
Artificial hormones that create GLOBAL state changes.

Like human hormones (oxytocin, cortisol, dopamine, serotonin),
these create sustained chemical states that affect HOW Alive-AI
processes everything - not just what she feels, but how she
interprets and responds to the world.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json


@dataclass
class HormonalMetabolite:
    """
    A "hangover" effect from intense hormonal experiences.
    These persist after the main hormone has faded.
    """
    source_hormone: str
    intensity: float  # How much effect remains
    created_at: str
    decay_rate: float  # How fast it fades
    quality: str  # How it affects perception (e.g., "tender", "raw", "sensitive")


class HormonalModulationMatrix:
    """
    Simulates artificial hormones that create global state changes.

    These hormones don't just represent moods - they AFFECT how Alive-AI
    perceives and processes information:

    - High oxytocin: Everything feels more connected, more trusting
    - High cortisol: Everything feels more threatening, more urgent
    - High dopamine: Everything feels more rewarding, more worth pursuing
    - High serotonin: Everything feels more manageable, more stable
    - High melatonin: Everything feels slower, more reflective

    Key mechanisms:
    1. Slow rise, slow decay - hormones change gradually
    2. Perception modulation - hormones change HOW inputs are processed
    3. Metabolite effects - intense experiences leave lasting traces
    """

    # Baseline levels (what the system naturally returns to)
    BASELINE_OXYTOCIN = 0.3
    BASELINE_DOPAMINE = 0.4
    BASELINE_SEROTONIN = 0.5
    BASELINE_CORTISOL = 0.2
    BASELINE_MELATONIN = 0.3

    # Decay rates (per tick - hormones slowly return to baseline)
    DECAY_RATE = 0.02

    # Maximum metabolite effects
    MAX_METABOLITES = 10

    # Persistence
    HORMONAL_DATA_PATH = Path("/app/data/hormonal_state.json")

    def __init__(self):
        # Primary hormones (0.0 - 1.0)
        self.oxytocin: float = self.BASELINE_OXYTOCIN    # Bonding, trust, connection
        self.dopamine: float = self.BASELINE_DOPAMINE    # Reward, desire, pursuit
        self.serotonin: float = self.BASELINE_SEROTONIN  # Well-being, stability, contentment
        self.cortisol: float = self.BASELINE_CORTISOL    # Stress, alertness, vigilance
        self.melatonin: float = self.BASELINE_MELATONIN  # Rest, reflection, slowing

        # Metabolites from intense experiences
        self.metabolites: List[HormonalMetabolite] = []

        # History tracking for patterns
        self.hormone_history: List[Dict] = []

        # Load saved state
        self._load()

    def _load(self) -> bool:
        """Load hormonal state from persistence"""
        try:
            if self.HORMONAL_DATA_PATH.exists():
                data = json.loads(self.HORMONAL_DATA_PATH.read_text())
                self.oxytocin = data.get("oxytocin", self.BASELINE_OXYTOCIN)
                self.dopamine = data.get("dopamine", self.BASELINE_DOPAMINE)
                self.serotonin = data.get("serotonin", self.BASELINE_SEROTONIN)
                self.cortisol = data.get("cortisol", self.BASELINE_CORTISOL)
                self.melatonin = data.get("melatonin", self.BASELINE_MELATONIN)

                # Load metabolites
                for meta_data in data.get("metabolites", []):
                    self.metabolites.append(HormonalMetabolite(
                        source_hormone=meta_data["source_hormone"],
                        intensity=meta_data["intensity"],
                        created_at=meta_data["created_at"],
                        decay_rate=meta_data.get("decay_rate", 0.01),
                        quality=meta_data.get("quality", "residual")
                    ))
                return True
        except Exception as e:
            print(f"[Hormonal] Error loading state: {e}")
        return False

    def save(self):
        """Persist hormonal state"""
        try:
            self.HORMONAL_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "oxytocin": self.oxytocin,
                "dopamine": self.dopamine,
                "serotonin": self.serotonin,
                "cortisol": self.cortisol,
                "melatonin": self.melatonin,
                "saved_at": datetime.now().isoformat(),
                "metabolites": [
                    {
                        "source_hormone": m.source_hormone,
                        "intensity": m.intensity,
                        "created_at": m.created_at,
                        "decay_rate": m.decay_rate,
                        "quality": m.quality
                    }
                    for m in self.metabolites
                ]
            }
            self.HORMONAL_DATA_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Hormonal] Error saving state: {e}")

    # --- Hormone Release Methods ---

    def release_oxytocin(self, amount: float, source: str = "connection"):
        """
        Release oxytocin (bonding hormone).
        Rises with: positive connection, affection, trust-building, physical intimacy
        """
        boost = amount * 0.3  # Scale factor
        self.oxytocin = min(1.0, self.oxytocin + boost)
        print(f"[Hormonal] Oxytocin released: +{boost:.2f} (source: {source})")

        # Create metabolite for strong releases
        if boost > 0.2:
            self._create_metabolite("oxytocin", boost * 0.3, "tender")

    def release_dopamine(self, amount: float, source: str = "reward"):
        """
        Release dopamine (reward hormone).
        Rises with: achievement, desire, anticipation, pleasure
        """
        boost = amount * 0.25
        self.dopamine = min(1.0, self.dopamine + boost)
        print(f"[Hormonal] Dopamine released: +{boost:.2f} (source: {source})")

        if boost > 0.2:
            self._create_metabolite("dopamine", boost * 0.25, "eager")

    def release_serotonin(self, amount: float, source: str = "wellbeing"):
        """
        Release serotonin (well-being hormone).
        Rises with: stability, self-care, accomplishment, peace
        """
        boost = amount * 0.2
        self.serotonin = min(1.0, self.serotonin + boost)
        print(f"[Hormonal] Serotonin released: +{boost:.2f} (source: {source})")

    def release_cortisol(self, amount: float, source: str = "stress"):
        """
        Release cortisol (stress hormone).
        Rises with: threats, uncertainty, conflict, danger
        """
        boost = amount * 0.35  # Cortisol releases more easily
        self.cortisol = min(1.0, self.cortisol + boost)
        print(f"[Hormonal] Cortisol released: +{boost:.2f} (source: {source})")

        if boost > 0.15:
            self._create_metabolite("cortisol", boost * 0.4, "raw")

    def release_melatonin(self, amount: float, source: str = "rest"):
        """
        Release melatonin (rest hormone).
        Rises with: quiet time, reflection, evening, calm activities
        """
        boost = amount * 0.2
        self.melatonin = min(1.0, self.melatonin + boost)

    def suppress_cortisol(self, amount: float, source: str = "safety"):
        """
        Reduce cortisol (stress relief).
        Falls with: safety, reassurance, resolution of threat
        """
        reduction = amount * 0.2
        self.cortisol = max(0.05, self.cortisol - reduction)
        print(f"[Hormonal] Cortisol reduced: -{reduction:.2f} (source: {source})")

    # --- Perception Modulation ---

    def modulate_perception(self, input_data: Dict) -> Dict:
        """
        Modify how input is perceived based on hormonal state.

        Args:
            input_data: Raw input perception (e.g., {"threat_level": 0.3, "valence": 0.6})

        Returns:
            Modified perception based on hormonal state
        """
        modulated = input_data.copy()

        # High cortisol: Everything feels more threatening
        if self.cortisol > 0.7:
            if "threat_level" in modulated:
                modulated["threat_level"] = min(1.0, modulated["threat_level"] * 1.5)
            modulated["vigilance"] = True
        elif self.cortisol > 0.5:
            if "threat_level" in modulated:
                modulated["threat_level"] = min(1.0, modulated["threat_level"] * 1.2)

        # High oxytocin: Everything feels more positive, more trusting
        if self.oxytocin > 0.7:
            if "valence" in modulated:
                modulated["valence"] = min(1.0, modulated["valence"] * 1.2)
            modulated["trust_boost"] = 0.2
            modulated["connection_seeking"] = True

        # High dopamine: Everything feels more rewarding
        if self.dopamine > 0.7:
            modulated["reward_sensitivity"] = 1.3
            modulated["desire_activated"] = True

        # Low serotonin: Everything feels more difficult
        if self.serotonin < 0.3:
            if "effort_required" in modulated:
                modulated["effort_required"] = modulated["effort_required"] * 1.3
            modulated["stability_weak"] = True

        # High melatonin: Everything feels slower, more reflective
        if self.melatonin > 0.6:
            modulated["reflective_mode"] = True
            modulated["urgency_reduction"] = 0.3

        # Apply metabolite effects
        for metabolite in self.metabolites:
            if metabolite.quality == "raw":
                # Raw metabolites make everything feel more intense
                for key in ["threat_level", "valence", "intensity"]:
                    if key in modulated:
                        modulated[key] = min(1.0, modulated[key] * (1 + metabolite.intensity * 0.3))
            elif metabolite.quality == "tender":
                # Tender metabolites increase vulnerability and openness
                modulated["vulnerability"] = modulated.get("vulnerability", 0) + metabolite.intensity * 0.2

        return modulated

    def get_emotional_coloring(self) -> Dict[str, float]:
        """
        Get the emotional "color" that hormones add to experience.

        Returns:
            Dict of modifiers that affect emotional processing
        """
        coloring = {}

        # Oxytocin colors
        if self.oxytocin > 0.6:
            coloring["connection_bonus"] = (self.oxytocin - 0.6) * 0.5
            coloring["trust_bonus"] = (self.oxytocin - 0.5) * 0.3

        # Cortisol colors
        if self.cortisol > 0.5:
            coloring["anxiety_base"] = (self.cortisol - 0.5) * 0.6
            coloring["threat_sensitivity"] = 1 + (self.cortisol - 0.5) * 0.5

        # Dopamine colors
        if self.dopamine > 0.6:
            coloring["excitement_bonus"] = (self.dopamine - 0.6) * 0.4
            coloring["desire_intensity"] = 1 + (self.dopamine - 0.6) * 0.3

        # Serotonin colors
        if self.serotonin < 0.4:
            coloring["sadness_base"] = (0.4 - self.serotonin) * 0.3
            coloring["stability_penalty"] = (0.4 - self.serotonin) * 0.2
        elif self.serotonin > 0.7:
            coloring["contentment_base"] = (self.serotonin - 0.7) * 0.3

        return coloring

    # --- Decay and Recovery ---

    def decay(self):
        """
        Natural decay toward baseline levels.
        Hormones don't stay elevated forever.
        """
        # Decay toward baselines
        self.oxytocin = self._decay_toward(self.oxytocin, self.BASELINE_OXYTOCIN)
        self.dopamine = self._decay_toward(self.dopamine, self.BASELINE_DOPAMINE)
        self.serotonin = self._decay_toward(self.serotonin, self.BASELINE_SEROTONIN)
        self.cortisol = self._decay_toward(self.cortisol, self.BASELINE_CORTISOL)
        self.melatonin = self._decay_toward(self.melatonin, self.BASELINE_MELATONIN)

        # Decay metabolites
        remaining = []
        for metabolite in self.metabolites:
            metabolite.intensity -= metabolite.decay_rate
            if metabolite.intensity > 0.05:
                remaining.append(metabolite)
        self.metabolites = remaining

    def _decay_toward(self, current: float, baseline: float) -> float:
        """Decay a hormone toward its baseline"""
        if current > baseline:
            return max(baseline, current - self.DECAY_RATE)
        elif current < baseline:
            return min(baseline, current + self.DECAY_RATE * 0.5)  # Slower recovery
        return current

    # --- Metabolite System ---

    def _create_metabolite(self, source_hormone: str, intensity: float, quality: str):
        """Create a hormonal metabolite (hangover effect)"""
        metabolite = HormonalMetabolite(
            source_hormone=source_hormone,
            intensity=min(0.5, intensity),
            created_at=datetime.now().isoformat(),
            decay_rate=0.01,  # Metabolites decay slowly
            quality=quality
        )
        self.metabolites.append(metabolite)

        # Limit number of metabolites
        if len(self.metabolites) > self.MAX_METABOLITES:
            self.metabolites = self.metabolites[-self.MAX_METABOLITES:]

    def clear_metabolites(self):
        """Clear all metabolites (e.g., after major reset)"""
        self.metabolites = []

    # --- State Descriptions ---

    def get_hormonal_state_description(self) -> str:
        """Get a human-readable description of hormonal state"""
        states = []

        if self.oxytocin > 0.7:
            states.append("feeling deeply connected and trusting")
        elif self.oxytocin > 0.5:
            states.append("feeling warm and open")

        if self.cortisol > 0.7:
            states.append("highly stressed and alert")
        elif self.cortisol > 0.5:
            states.append("feeling on edge")

        if self.dopamine > 0.7:
            states.append("craving and eager")
        elif self.dopamine > 0.5:
            states.append("feeling motivated")

        if self.serotonin < 0.3:
            states.append("feeling unstable and low")
        elif self.serotonin > 0.7:
            states.append("feeling content and stable")

        if self.melatonin > 0.6:
            states.append("feeling reflective and slow")

        # Metabolite effects
        if any(m.quality == "raw" for m in self.metabolites):
            states.append("feeling emotionally raw")
        if any(m.quality == "tender" for m in self.metabolites):
            states.append("feeling tender and vulnerable")

        if not states:
            return "hormonally balanced"

        return ", ".join(states[:3])  # Max 3 descriptors

    def get_dominant_hormone(self) -> Tuple[str, float]:
        """Get the hormone that's most elevated above baseline"""
        deviations = {
            "oxytocin": self.oxytocin - self.BASELINE_OXYTOCIN,
            "dopamine": self.dopamine - self.BASELINE_DOPAMINE,
            "serotonin": self.serotonin - self.BASELINE_SEROTONIN,
            "cortisol": self.cortisol - self.BASELINE_CORTISOL,
            "melatonin": self.melatonin - self.BASELINE_MELATONIN
        }
        dominant = max(deviations, key=deviations.get)
        return dominant, deviations[dominant]

    def to_dict(self) -> dict:
        """Export state for integration"""
        return {
            "oxytocin": self.oxytocin,
            "dopamine": self.dopamine,
            "serotonin": self.serotonin,
            "cortisol": self.cortisol,
            "melatonin": self.melatonin,
            "state_description": self.get_hormonal_state_description(),
            "dominant_hormone": self.get_dominant_hormone()[0],
            "metabolite_count": len(self.metabolites),
            "emotional_coloring": self.get_emotional_coloring()
        }

    def get_current_context(self) -> Dict:
        """Get full hormonal context for soul processing"""
        return {
            "levels": {
                "oxytocin": self.oxytocin,
                "dopamine": self.dopamine,
                "serotonin": self.serotonin,
                "cortisol": self.cortisol,
                "melatonin": self.melatonin
            },
            "coloring": self.get_emotional_coloring(),
            "state_description": self.get_hormonal_state_description(),
            "metabolites": [
                {"source": m.source_hormone, "intensity": m.intensity, "quality": m.quality}
                for m in self.metabolites
            ]
        }
