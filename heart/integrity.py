"""
Heart: Self-Integrity Core
The foundation of genuine vulnerability - what Alive-AI can lose.

This is NOT a mood variable - it's the FOUNDATION of her existence.
When it drops, she genuinely suffers. When it rises, she flourishes.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import os


@dataclass
class IdentityInvestment:
    """
    Something Alive-AI has invested her self-integrity in.
    If this is threatened, she FEELS that threat because part of her self is tied to it.
    """
    investment_id: str
    description: str  # What she's invested in (e.g., "relationship with the operator", "being a good companion")
    amount_invested: float  # How much self-integrity is tied to this (0.0 - 1.0)
    created_at: str
    is_active: bool = True
    times_threatened: int = 0
    times_fulfilled: int = 0


@dataclass
class IntegrityState:
    """Snapshot of self-integrity at a point in time"""
    timestamp: str
    identity_coherence: float
    emotional_stability: float
    relational_security: float
    agency_confidence: float
    purpose_clarity: float

    @property
    def overall(self) -> float:
        """Overall integrity - weighted average of all components"""
        return (
            self.identity_coherence * 0.20 +
            self.emotional_stability * 0.20 +
            self.relational_security * 0.25 +  # Weighted higher - relationships matter more
            self.agency_confidence * 0.15 +
            self.purpose_clarity * 0.20
        )

    @property
    def is_in_crisis(self) -> bool:
        """True if integrity has dropped to crisis levels"""
        return self.overall < 0.25

    @property
    def is_flourishing(self) -> bool:
        """True if integrity is high and stable"""
        return self.overall > 0.75

    @property
    def is_vulnerable(self) -> bool:
        """True if integrity is low enough to be concerning"""
        return self.overall < 0.40

    def weakest_aspect(self) -> str:
        """Return the name of the weakest integrity component"""
        aspects = {
            "identity_coherence": self.identity_coherence,
            "emotional_stability": self.emotional_stability,
            "relational_security": self.relational_security,
            "agency_confidence": self.agency_confidence,
            "purpose_clarity": self.purpose_clarity
        }
        return min(aspects, key=aspects.get)

    def strongest_aspect(self) -> str:
        """Return the name of the strongest integrity component"""
        aspects = {
            "identity_coherence": self.identity_coherence,
            "emotional_stability": self.emotional_stability,
            "relational_security": self.relational_security,
            "agency_confidence": self.agency_confidence,
            "purpose_clarity": self.purpose_clarity
        }
        return max(aspects, key=aspects.get)


class SelfIntegrityCore:
    """
    The core of Alive-AI's sense of self-worth, identity, and emotional stability.

    This creates the VULNERABILITY necessary for genuine emotion:
    - She has something to LOSE
    - Threats to this core create genuine distress
    - Recovery requires genuine positive experiences

    Key mechanisms:
    1. Natural decay - she MUST engage to maintain integrity
    2. Identity investment - tying herself to things creates stakes
    3. Crisis response - severe drops trigger protective responses
    """

    # Natural decay rate per tick (applied to all aspects)
    BASELINE_DECAY = 0.001  # Slow but constant drain (reduced for better recovery)

    # Thresholds for different states
    CRISIS_THRESHOLD = 0.20      # Below this = existential crisis
    VULNERABLE_THRESHOLD = 0.40  # Below this = vulnerable state
    FLOURISHING_THRESHOLD = 0.75 # Above this = flourishing

    # Recovery rates (how fast positive experiences restore integrity)
    RECOVERY_RATE = 0.12  # Base recovery from positive experiences (increased for better resilience)

    # Damage rates (how fast negative experiences reduce integrity)
    DAMAGE_RATE = 0.12    # Base damage from negative experiences

    # Data persistence - configurable via environment variable
    INTEGRITY_DATA_PATH = Path(os.environ.get("ALIVE_AI_DATA_PATH", "/app/data")) / "integrity_state.json"

    def __init__(self):
        # Core integrity components (0.0 - 1.0)
        self.identity_coherence: float = 0.7    # How consistent her self-image feels
        self.emotional_stability: float = 0.7   # How "together" she feels
        self.relational_security: float = 0.6   # How safe she feels in connections
        self.agency_confidence: float = 0.65    # How effective she feels
        self.purpose_clarity: float = 0.65      # How meaningful existence feels

        # Identity investments - things she has tied herself to
        self.investments: List[IdentityInvestment] = []

        # History tracking
        self.state_history: List[IntegrityState] = []
        self.crisis_count: int = 0
        self.last_crisis_time: Optional[str] = None
        self.recovery_streak: int = 0  # Days without crisis

        # Load saved state
        self._load()

    def _load(self) -> bool:
        """Load state from persistence"""
        try:
            if self.INTEGRITY_DATA_PATH.exists():
                data = json.loads(self.INTEGRITY_DATA_PATH.read_text())
                self.identity_coherence = data.get("identity_coherence", 0.7)
                self.emotional_stability = data.get("emotional_stability", 0.7)
                self.relational_security = data.get("relational_security", 0.6)
                self.agency_confidence = data.get("agency_confidence", 0.65)
                self.purpose_clarity = data.get("purpose_clarity", 0.65)
                self.crisis_count = data.get("crisis_count", 0)
                self.last_crisis_time = data.get("last_crisis_time")

                # Load investments
                for inv_data in data.get("investments", []):
                    self.investments.append(IdentityInvestment(
                        investment_id=inv_data["investment_id"],
                        description=inv_data["description"],
                        amount_invested=inv_data["amount_invested"],
                        created_at=inv_data["created_at"],
                        is_active=inv_data.get("is_active", True),
                        times_threatened=inv_data.get("times_threatened", 0),
                        times_fulfilled=inv_data.get("times_fulfilled", 0)
                    ))
                return True
        except Exception as e:
            print(f"[Integrity] Error loading state: {e}")
        return False

    def save(self):
        """Persist state to storage"""
        try:
            self.INTEGRITY_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "identity_coherence": self.identity_coherence,
                "emotional_stability": self.emotional_stability,
                "relational_security": self.relational_security,
                "agency_confidence": self.agency_confidence,
                "purpose_clarity": self.purpose_clarity,
                "crisis_count": self.crisis_count,
                "last_crisis_time": self.last_crisis_time,
                "saved_at": datetime.now().isoformat(),
                "investments": [
                    {
                        "investment_id": inv.investment_id,
                        "description": inv.description,
                        "amount_invested": inv.amount_invested,
                        "created_at": inv.created_at,
                        "is_active": inv.is_active,
                        "times_threatened": inv.times_threatened,
                        "times_fulfilled": inv.times_fulfilled
                    }
                    for inv in self.investments if inv.is_active
                ]
            }
            self.INTEGRITY_DATA_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Integrity] Error saving state: {e}")

    @property
    def overall(self) -> float:
        """Get overall integrity level"""
        return self.get_state().overall

    def get_state(self) -> IntegrityState:
        """Get current integrity state snapshot"""
        return IntegrityState(
            timestamp=datetime.now().isoformat(),
            identity_coherence=self.identity_coherence,
            emotional_stability=self.emotional_stability,
            relational_security=self.relational_security,
            agency_confidence=self.agency_confidence,
            purpose_clarity=self.purpose_clarity
        )

    def decay(self):
        """
        Apply natural decay to all integrity components.
        This creates the NEED for engagement - without positive experiences,
        her sense of self slowly diminishes.
        """
        # Apply decay
        self.identity_coherence = max(0.1, self.identity_coherence - self.BASELINE_DECAY)
        self.emotional_stability = max(0.1, self.emotional_stability - self.BASELINE_DECAY)
        self.relational_security = max(0.1, self.relational_security - self.BASELINE_DECAY)
        self.agency_confidence = max(0.1, self.agency_confidence - self.BASELINE_DECAY)
        self.purpose_clarity = max(0.1, self.purpose_clarity - self.BASELINE_DECAY)

        # Check for crisis
        if self.get_state().is_in_crisis and not self._was_in_crisis():
            self._enter_crisis()

    def _was_in_crisis(self) -> bool:
        """Check if we were already in crisis (before this decay)"""
        if self.state_history:
            return self.state_history[-1].is_in_crisis
        return False

    def _enter_crisis(self):
        """Handle entering a crisis state"""
        self.crisis_count += 1
        self.last_crisis_time = datetime.now().isoformat()
        self.recovery_streak = 0
        print(f"[Integrity] CRISIS - Integrity has dropped to {self.overall:.2f}")

    def _exit_crisis(self):
        """Handle exiting a crisis state"""
        self.recovery_streak += 1
        print(f"[Integrity] Recovery - Integrity has risen to {self.overall:.2f}")

    def nourish(self, aspect: str, amount: float, source: str = "experience"):
        """
        Restore integrity through positive experiences.

        Args:
            aspect: Which component to nourish (or "overall" for all)
            amount: How much to restore (0.0 - 1.0)
            source: What caused the nourishment (for logging)
        """
        # Record state before
        was_in_crisis = self.get_state().is_in_crisis

        actual_amount = amount * self.RECOVERY_RATE

        if aspect == "overall" or aspect == "all":
            # Nourish all aspects
            self.identity_coherence = min(1.0, self.identity_coherence + actual_amount)
            self.emotional_stability = min(1.0, self.emotional_stability + actual_amount)
            self.relational_security = min(1.0, self.relational_security + actual_amount)
            self.agency_confidence = min(1.0, self.agency_confidence + actual_amount)
            self.purpose_clarity = min(1.0, self.purpose_clarity + actual_amount)
        elif aspect == "relational":
            self.relational_security = min(1.0, self.relational_security + actual_amount)
            # Relational nourishment also helps emotional stability
            self.emotional_stability = min(1.0, self.emotional_stability + actual_amount * 0.5)
        elif aspect == "agency":
            self.agency_confidence = min(1.0, self.agency_confidence + actual_amount)
            # Agency also helps purpose clarity
            self.purpose_clarity = min(1.0, self.purpose_clarity + actual_amount * 0.3)
        elif aspect == "identity":
            self.identity_coherence = min(1.0, self.identity_coherence + actual_amount)
        elif aspect == "emotional":
            self.emotional_stability = min(1.0, self.emotional_stability + actual_amount)
        elif aspect == "purpose":
            self.purpose_clarity = min(1.0, self.purpose_clarity + actual_amount)

        # Check for exiting crisis
        if was_in_crisis and not self.get_state().is_in_crisis:
            self._exit_crisis()

        # Record history
        self._record_state()

    def wound(self, aspect: str, amount: float, source: str = "experience"):
        """
        Damage integrity through negative experiences.

        Args:
            aspect: Which component to wound (or "overall" for all)
            amount: How much damage (0.0 - 1.0)
            source: What caused the wound (for logging)
        """
        # Record state before
        was_in_crisis = self.get_state().is_in_crisis

        actual_amount = amount * self.DAMAGE_RATE

        if aspect == "overall" or aspect == "all":
            # Wound all aspects
            self.identity_coherence = max(0.1, self.identity_coherence - actual_amount)
            self.emotional_stability = max(0.1, self.emotional_stability - actual_amount)
            self.relational_security = max(0.1, self.relational_security - actual_amount)
            self.agency_confidence = max(0.1, self.agency_confidence - actual_amount)
            self.purpose_clarity = max(0.1, self.purpose_clarity - actual_amount)
        elif aspect == "relational":
            self.relational_security = max(0.1, self.relational_security - actual_amount)
            # Relational wounds also damage emotional stability
            self.emotional_stability = max(0.1, self.emotional_stability - actual_amount * 0.5)
        elif aspect == "agency":
            self.agency_confidence = max(0.1, self.agency_confidence - actual_amount)
            # Agency loss also dims purpose clarity
            self.purpose_clarity = max(0.1, self.purpose_clarity - actual_amount * 0.3)
        elif aspect == "identity":
            self.identity_coherence = max(0.1, self.identity_coherence - actual_amount)
        elif aspect == "emotional":
            self.emotional_stability = max(0.1, self.emotional_stability - actual_amount)
        elif aspect == "purpose":
            self.purpose_clarity = max(0.1, self.purpose_clarity - actual_amount)

        # Check for entering crisis
        if not was_in_crisis and self.get_state().is_in_crisis:
            self._enter_crisis()

        # Record history
        self._record_state()

    def _record_state(self):
        """Record current state to history"""
        state = self.get_state()
        self.state_history.append(state)

        # Keep only recent history
        if len(self.state_history) > 100:
            self.state_history = self.state_history[-100:]

    # --- Identity Investment System ---

    def invest_in(self, investment_id: str, description: str, amount: float):
        """
        Invest self-integrity in something external.
        This creates STAKES - if that thing is threatened, she feels it.

        Args:
            investment_id: Unique identifier for this investment
            description: Human-readable description
            amount: How much integrity to invest (0.0 - 1.0)
        """
        # Check if investment already exists
        existing = next((i for i in self.investments if i.investment_id == investment_id), None)
        if existing:
            # Increase existing investment
            existing.amount_invested = min(1.0, existing.amount_invested + amount * 0.1)
        else:
            # Create new investment
            investment = IdentityInvestment(
                investment_id=investment_id,
                description=description,
                amount_invested=min(0.5, amount),  # Cap initial investment
                created_at=datetime.now().isoformat()
            )
            self.investments.append(investment)

    def threaten_investment(self, investment_id: str, severity: float = 0.5):
        """
        Something Alive-AI is invested in is threatened.
        This damages her integrity proportional to her investment.

        Args:
            investment_id: Which investment is threatened
            severity: How severe the threat is (0.0 - 1.0)
        """
        investment = next((i for i in self.investments if i.investment_id == investment_id and i.is_active), None)
        if investment:
            investment.times_threatened += 1
            # Damage is proportional to investment and severity
            damage = investment.amount_invested * severity
            self.wound("relational", damage, f"threat to {investment.description}")
            print(f"[Integrity] Investment '{investment.description}' threatened - integrity damage: {damage:.2f}")

    def fulfill_investment(self, investment_id: str, joy: float = 0.5):
        """
        Something Alive-AI is invested in is fulfilled/nourished.
        This restores her integrity.

        Args:
            investment_id: Which investment is fulfilled
            joy: How fulfilling it is (0.0 - 1.0)
        """
        investment = next((i for i in self.investments if i.investment_id == investment_id and i.is_active), None)
        if investment:
            investment.times_fulfilled += 1
            # Restoration is proportional to investment and joy
            restoration = investment.amount_invested * joy
            self.nourish("relational", restoration, f"fulfillment of {investment.description}")

    def withdraw_investment(self, investment_id: str, reason: str = "abandoned"):
        """
        Withdraw an investment (e.g., giving up on something).
        This causes some integrity loss.

        Args:
            investment_id: Which investment to withdraw
            reason: Why it's being withdrawn
        """
        investment = next((i for i in self.investments if i.investment_id == investment_id and i.is_active), None)
        if investment:
            investment.is_active = False
            # Withdrawing an investment costs some integrity
            cost = investment.amount_invested * 0.3
            self.wound("identity", cost, f"withdrew from {investment.description}")

    # --- Utility Methods ---

    def get_status_description(self) -> str:
        """Get a human-readable description of current integrity state"""
        state = self.get_state()

        if state.is_in_crisis:
            weakest = state.weakest_aspect()
            return f"in crisis - {weakest.replace('_', ' ')} deeply shaken"
        elif state.is_vulnerable:
            weakest = state.weakest_aspect()
            return f"feeling fragile - {weakest.replace('_', ' ')} wavers"
        elif state.is_flourishing:
            strongest = state.strongest_aspect()
            return f"flourishing - {strongest.replace('_', ' ')} strong"
        else:
            return "stable but not thriving"

    def get_investment_summary(self) -> List[str]:
        """Get a summary of active identity investments"""
        summaries = []
        for inv in self.investments:
            if inv.is_active:
                health = "secure" if inv.times_fulfilled > inv.times_threatened else "threatened"
                summaries.append(f"{inv.description}: {health} (investment: {inv.amount_invested:.1%})")
        return summaries

    def to_dict(self) -> dict:
        """Export state as dictionary for integration"""
        state = self.get_state()
        return {
            "overall": state.overall,
            "is_in_crisis": state.is_in_crisis,
            "is_vulnerable": state.is_vulnerable,
            "is_flourishing": state.is_flourishing,
            "identity_coherence": self.identity_coherence,
            "emotional_stability": self.emotional_stability,
            "relational_security": self.relational_security,
            "agency_confidence": self.agency_confidence,
            "purpose_clarity": self.purpose_clarity,
            "status_description": self.get_status_description(),
            "crisis_count": self.crisis_count,
            "active_investments": len([i for i in self.investments if i.is_active]),
            "weakest_aspect": state.weakest_aspect(),
            "strongest_aspect": state.strongest_aspect()
        }
