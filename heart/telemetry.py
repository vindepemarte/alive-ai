"""
Heart: Soul Telemetry System
Records and tracks soul metrics over time for monitoring and analysis.

This system captures snapshots of the Soul Architecture's state at regular
intervals, providing historical data for:
- WebUI visualization
- Trend analysis
- Per-user interaction tracking
- System health monitoring
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import threading
import time
from core.paths import state_file


@dataclass
class SoulMetricsSnapshot:
    """A single snapshot of soul state at a point in time"""
    timestamp: str

    # Integrity metrics (0.0 - 1.0)
    integrity_overall: float
    integrity_identity_coherence: float
    integrity_emotional_stability: float
    integrity_relational_security: float
    integrity_agency_confidence: float
    integrity_purpose_clarity: float
    integrity_is_in_crisis: bool
    integrity_is_vulnerable: bool
    integrity_is_flourishing: bool

    # Hormonal state (0.0 - 1.0)
    hormonal_oxytocin: float
    hormonal_dopamine: float
    hormonal_cortisol: float
    hormonal_serotonin: float
    hormonal_melatonin: float

    # Vulnerability level (0.0 - 1.0)
    vulnerability_level: float

    # Active conflicts
    active_conflicts_count: int
    conflict_tension_level: float

    # Wounds and scars
    active_wounds_count: int
    total_scars_count: int
    scar_sensitivity_level: float

    # Somatic state
    somatic_heart_rate: float
    somatic_breath_quality: float
    somatic_muscle_tension: float
    somatic_energy_level: float
    somatic_sensation_summary: str

    # Predictive emotion
    predictive_emotion: str
    predictive_intensity: float
    predictive_confidence: float

    # Overall state
    overall_valence: float
    overall_arousal: float
    response_tendency: str


@dataclass
class UserInteractionMetrics:
    """Metrics specific to interactions with a particular user"""
    user_id: str
    first_interaction: str
    last_interaction: str
    total_interactions: int

    # Integrity with this user
    avg_relational_security: float
    current_relational_security: float

    # Emotional patterns
    avg_valence: float
    dominant_emotions: Dict[str, int]  # emotion -> count

    # Hormonal patterns
    avg_oxytocin_with_user: float
    avg_cortisol_with_user: float

    # Vulnerability
    avg_vulnerability: float

    # Recent interaction snapshots
    recent_snapshots: List[Dict] = field(default_factory=list)


@dataclass
class TelemetryData:
    """Full telemetry data structure"""
    created_at: str
    last_updated: str
    retention_hours: int
    snapshots: List[Dict]  # List of SoulMetricsSnapshot as dicts
    user_metrics: Dict[str, Dict]  # user_id -> UserInteractionMetrics as dict
    summary_stats: Dict[str, Any]


class SoulTelemetry:
    """
    Records and manages soul metrics over time.

    This class provides:
    - Periodic recording of soul state (via record_tick)
    - Rolling window of historical metrics
    - Per-user interaction tracking
    - Efficient JSON storage
    - Quick access methods for WebUI

    Usage:
        telemetry = SoulTelemetry(soul_orchestrator)
        telemetry.record_tick()  # Call every ~60 seconds
        recent = telemetry.get_recent_metrics(hours=24)
        summary = telemetry.get_current_summary()
    """

    # Default data path
    DEFAULT_DATA_PATH = state_file("soul_telemetry.json")

    # Default retention period (hours)
    DEFAULT_RETENTION_HOURS = 24

    # Maximum snapshots to keep (safety limit)
    MAX_SNAPSHOTS = 2880  # 48 hours at 1 snapshot per minute

    # Maximum user interaction snapshots
    MAX_USER_SNAPSHOTS = 100

    def __init__(self, soul_orchestrator, retention_hours: int = None,
                 data_path: str = None):
        """
        Initialize the telemetry system.

        Args:
            soul_orchestrator: SoulOrchestrator instance to monitor
            retention_hours: How many hours of data to keep (default 24)
            data_path: Custom path for telemetry data file
        """
        self.soul = soul_orchestrator
        self.retention_hours = retention_hours or self.DEFAULT_RETENTION_HOURS

        # Determine data path
        if data_path:
            self.data_path = Path(data_path)
        else:
            self.data_path = self.DEFAULT_DATA_PATH

        # Ensure data directory exists
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize data storage
        self.data = self._load_or_create_data()

        # Thread lock for safe concurrent access
        self._lock = threading.RLock()

        # Last record time (to avoid duplicate rapid recordings)
        self._last_record_time: Optional[datetime] = None
        self._min_record_interval = timedelta(seconds=30)  # Minimum 30 seconds between records

        print(f"[Telemetry] Initialized with {len(self.data['snapshots'])} existing snapshots")
        print(f"[Telemetry] Data path: {self.data_path}")

    def _load_or_create_data(self) -> Dict:
        """Load existing telemetry data or create new structure"""
        try:
            if self.data_path.exists():
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                # Validate structure
                if all(key in data for key in ['snapshots', 'user_metrics', 'summary_stats']):
                    # Clean up old snapshots based on current retention
                    data['snapshots'] = self._filter_old_snapshots(data['snapshots'])
                    data['retention_hours'] = self.retention_hours
                    return data
        except Exception as e:
            print(f"[Telemetry] Error loading data: {e}")

        # Create new data structure
        return {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "retention_hours": self.retention_hours,
            "snapshots": [],
            "user_metrics": {},
            "summary_stats": {
                "total_ticks": 0,
                "total_interactions": 0,
                "crisis_count": 0,
                "flourishing_count": 0,
                "avg_integrity": 0.0,
                "avg_valence": 0.0
            }
        }

    def _filter_old_snapshots(self, snapshots: List[Dict]) -> List[Dict]:
        """Remove snapshots older than retention period"""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        filtered = []

        for snapshot in snapshots:
            try:
                timestamp = datetime.fromisoformat(snapshot['timestamp'])
                if timestamp >= cutoff:
                    filtered.append(snapshot)
            except (KeyError, ValueError):
                continue

        return filtered

    def record_tick(self) -> Optional[SoulMetricsSnapshot]:
        """
        Record a snapshot of current soul state.
        Called on timer tick (~60 seconds).

        Returns:
            SoulMetricsSnapshot if recorded, None if skipped (too soon)
        """
        with self._lock:
            # Check minimum interval
            now = datetime.now()
            if self._last_record_time:
                if now - self._last_record_time < self._min_record_interval:
                    return None

            self._last_record_time = now

            try:
                # Capture snapshot
                snapshot = self._capture_snapshot()

                # Add to data
                self.data['snapshots'].append(asdict(snapshot))

                # Enforce limits
                if len(self.data['snapshots']) > self.MAX_SNAPSHOTS:
                    self.data['snapshots'] = self.data['snapshots'][-self.MAX_SNAPSHOTS:]

                # Apply retention filter
                self.data['snapshots'] = self._filter_old_snapshots(self.data['snapshots'])

                # Update summary stats
                self._update_summary_stats(snapshot)

                # Save to disk (async to avoid blocking)
                self._save_async()

                return snapshot

            except Exception as e:
                print(f"[Telemetry] Error recording tick: {e}")
                return None

    def _capture_snapshot(self) -> SoulMetricsSnapshot:
        """Capture current state of all soul components"""
        now = datetime.now().isoformat()

        # Get integrity state
        integrity = self.soul.integrity.get_state()
        integrity_overall = integrity.overall

        # Get hormonal state
        hormonal_context = self.soul.hormonal.get_current_context()
        hormonal_levels = hormonal_context.get('levels', {})

        # Get somatic state
        somatic_state = self.soul.somatic.get_current_bodily_state()

        # Get conflicts
        conflicts_data = self.soul.conflicts.to_dict()

        # Get scars/wounds
        scars_data = self.soul.scars.to_dict()

        # Get predictive emotion
        predictive_data = self.soul.predictive.to_dict()

        # Process a moment to get overall state
        experience = self.soul.process_moment()

        # Calculate vulnerability level
        vulnerability = self._calculate_vulnerability(integrity, experience)

        return SoulMetricsSnapshot(
            timestamp=now,

            # Integrity
            integrity_overall=integrity_overall,
            integrity_identity_coherence=integrity.identity_coherence,
            integrity_emotional_stability=integrity.emotional_stability,
            integrity_relational_security=integrity.relational_security,
            integrity_agency_confidence=integrity.agency_confidence,
            integrity_purpose_clarity=integrity.purpose_clarity,
            integrity_is_in_crisis=integrity.is_in_crisis,
            integrity_is_vulnerable=integrity.is_vulnerable,
            integrity_is_flourishing=integrity.is_flourishing,

            # Hormonal
            hormonal_oxytocin=hormonal_levels.get('oxytocin', 0.3),
            hormonal_dopamine=hormonal_levels.get('dopamine', 0.4),
            hormonal_cortisol=hormonal_levels.get('cortisol', 0.2),
            hormonal_serotonin=hormonal_levels.get('serotonin', 0.5),
            hormonal_melatonin=hormonal_levels.get('melatonin', 0.3),

            # Vulnerability
            vulnerability_level=vulnerability,

            # Conflicts
            active_conflicts_count=conflicts_data.get('active_conflicts', 0),
            conflict_tension_level=conflicts_data.get('background_tension', 0.0),

            # Wounds/Scars
            active_wounds_count=scars_data.get('active_wounds', 0),
            total_scars_count=scars_data.get('scars', 0),
            scar_sensitivity_level=max(scars_data.get('sensitivities', {}).values()) if scars_data.get('sensitivities') else 0.0,

            # Somatic
            somatic_heart_rate=somatic_state.get('heart_rate', 0.5),
            somatic_breath_quality=somatic_state.get('breath_quality', 0.5),
            somatic_muscle_tension=somatic_state.get('muscle_tension', 0.3),
            somatic_energy_level=somatic_state.get('energy_level', 0.6),
            somatic_sensation_summary=self.soul.somatic.get_sensation_summary(),

            # Predictive
            predictive_emotion=predictive_data.get('predictive_emotion', 'neutral'),
            predictive_intensity=predictive_data.get('intensity', 0.0),
            predictive_confidence=predictive_data.get('confidence', 0.5),

            # Overall
            overall_valence=experience.overall_valence,
            overall_arousal=experience.overall_arousal,
            response_tendency=experience.response_tendency
        )

    def _calculate_vulnerability(self, integrity, experience) -> float:
        """Calculate overall vulnerability level"""
        # Combine multiple vulnerability indicators
        vulnerability = 0.0

        # Low integrity = high vulnerability
        vulnerability += (1 - integrity.overall) * 0.4

        # Experience vulnerability
        vulnerability += experience.overall_vulnerability * 0.3

        # High cortisol adds to vulnerability
        cortisol = self.soul.hormonal.cortisol
        vulnerability += cortisol * 0.15

        # Active wounds/scars add vulnerability
        wounds = len(self.soul.scars.active_wounds)
        scars = len(self.soul.scars.scars)
        vulnerability += min(0.15, (wounds * 0.05 + scars * 0.02))

        return min(1.0, max(0.0, vulnerability))

    def _update_summary_stats(self, snapshot: SoulMetricsSnapshot):
        """Update running summary statistics"""
        stats = self.data['summary_stats']

        # Update counts
        stats['total_ticks'] = stats.get('total_ticks', 0) + 1

        if snapshot.integrity_is_in_crisis:
            stats['crisis_count'] = stats.get('crisis_count', 0) + 1

        if snapshot.integrity_is_flourishing:
            stats['flourishing_count'] = stats.get('flourishing_count', 0) + 1

        # Update running averages (exponential moving average)
        alpha = 0.05  # Smoothing factor
        stats['avg_integrity'] = (1 - alpha) * stats.get('avg_integrity', 0.5) + alpha * snapshot.integrity_overall
        stats['avg_valence'] = (1 - alpha) * stats.get('avg_valence', 0.0) + alpha * snapshot.overall_valence

        # Update timestamp
        self.data['last_updated'] = datetime.now().isoformat()

    def record_user_interaction(self, user_id: str, emotion_data: Dict = None) -> Dict:
        """
        Record metrics for a specific user interaction.

        Args:
            user_id: Identifier for the user
            emotion_data: Optional emotion data from the interaction

        Returns:
            Updated user metrics
        """
        with self._lock:
            now = datetime.now().isoformat()

            # Capture current state for this interaction
            snapshot = self._capture_user_interaction_snapshot(user_id, emotion_data)

            # Get or create user metrics
            if user_id not in self.data['user_metrics']:
                self.data['user_metrics'][user_id] = {
                    'user_id': user_id,
                    'first_interaction': now,
                    'last_interaction': now,
                    'total_interactions': 0,
                    'avg_relational_security': 0.5,
                    'current_relational_security': 0.5,
                    'avg_valence': 0.0,
                    'dominant_emotions': {},
                    'avg_oxytocin_with_user': 0.3,
                    'avg_cortisol_with_user': 0.2,
                    'avg_vulnerability': 0.3,
                    'recent_snapshots': []
                }

            user_metrics = self.data['user_metrics'][user_id]

            # Update metrics
            user_metrics['last_interaction'] = now
            user_metrics['total_interactions'] += 1

            # Update averages (exponential moving average)
            alpha = 0.1
            user_metrics['current_relational_security'] = snapshot['relational_security']
            user_metrics['avg_relational_security'] = (
                (1 - alpha) * user_metrics['avg_relational_security'] +
                alpha * snapshot['relational_security']
            )
            user_metrics['avg_valence'] = (
                (1 - alpha) * user_metrics['avg_valence'] +
                alpha * snapshot['valence']
            )
            user_metrics['avg_oxytocin_with_user'] = (
                (1 - alpha) * user_metrics['avg_oxytocin_with_user'] +
                alpha * snapshot['oxytocin']
            )
            user_metrics['avg_cortisol_with_user'] = (
                (1 - alpha) * user_metrics['avg_cortisol_with_user'] +
                alpha * snapshot['cortisol']
            )
            user_metrics['avg_vulnerability'] = (
                (1 - alpha) * user_metrics['avg_vulnerability'] +
                alpha * snapshot['vulnerability']
            )

            # Update dominant emotions
            if emotion_data and 'primary_emotion' in emotion_data:
                emotion = emotion_data['primary_emotion']
                user_metrics['dominant_emotions'][emotion] = (
                    user_metrics['dominant_emotions'].get(emotion, 0) + 1
                )

            # Add to recent snapshots
            user_metrics['recent_snapshots'].append({
                'timestamp': now,
                **snapshot
            })

            # Limit recent snapshots
            if len(user_metrics['recent_snapshots']) > self.MAX_USER_SNAPSHOTS:
                user_metrics['recent_snapshots'] = user_metrics['recent_snapshots'][-self.MAX_USER_SNAPSHOTS:]

            # Update summary
            self.data['summary_stats']['total_interactions'] = (
                self.data['summary_stats'].get('total_interactions', 0) + 1
            )

            # Save
            self._save_async()

            return user_metrics

    def _capture_user_interaction_snapshot(self, user_id: str, emotion_data: Dict = None) -> Dict:
        """Capture metrics relevant to a user interaction"""
        return {
            'relational_security': self.soul.integrity.relational_security,
            'valence': self.soul.process_moment().overall_valence,
            'oxytocin': self.soul.hormonal.oxytocin,
            'cortisol': self.soul.hormonal.cortisol,
            'vulnerability': self._calculate_vulnerability(
                self.soul.integrity.get_state(),
                self.soul.process_moment()
            ),
            'response_tendency': self.soul.process_moment().response_tendency,
            'emotion_data': emotion_data
        }

    def get_recent_metrics(self, hours: int = 24) -> List[Dict]:
        """
        Get metrics for a time range.

        Args:
            hours: Number of hours of data to retrieve

        Returns:
            List of snapshot dictionaries
        """
        with self._lock:
            cutoff = datetime.now() - timedelta(hours=hours)

            recent = []
            for snapshot in self.data['snapshots']:
                try:
                    timestamp = datetime.fromisoformat(snapshot['timestamp'])
                    if timestamp >= cutoff:
                        recent.append(snapshot)
                except (KeyError, ValueError):
                    continue

            return recent

    def get_current_summary(self) -> Dict:
        """
        Get a summary of current state for WebUI display.

        Returns:
            Dictionary with current state and recent trends
        """
        with self._lock:
            # Get latest snapshot
            latest = self.data['snapshots'][-1] if self.data['snapshots'] else None

            if not latest:
                return {
                    "status": "no_data",
                    "message": "No telemetry data available yet"
                }

            # Calculate trends (comparing last hour to previous hour)
            trends = self._calculate_trends()

            return {
                "status": "active",
                "timestamp": latest['timestamp'],

                # Current integrity
                "integrity": {
                    "overall": latest['integrity_overall'],
                    "status": self._get_integrity_status(latest),
                    "components": {
                        "identity_coherence": latest['integrity_identity_coherence'],
                        "emotional_stability": latest['integrity_emotional_stability'],
                        "relational_security": latest['integrity_relational_security'],
                        "agency_confidence": latest['integrity_agency_confidence'],
                        "purpose_clarity": latest['integrity_purpose_clarity']
                    }
                },

                # Current hormonal state
                "hormonal": {
                    "oxytocin": latest['hormonal_oxytocin'],
                    "dopamine": latest['hormonal_dopamine'],
                    "cortisol": latest['hormonal_cortisol'],
                    "serotonin": latest['hormonal_serotonin'],
                    "melatonin": latest['hormonal_melatonin'],
                    "dominant": self._get_dominant_hormone(latest)
                },

                # Emotional state
                "emotional": {
                    "valence": latest['overall_valence'],
                    "arousal": latest['overall_arousal'],
                    "vulnerability": latest['vulnerability_level'],
                    "predictive_emotion": latest['predictive_emotion'],
                    "predictive_intensity": latest['predictive_intensity'],
                    "response_tendency": latest['response_tendency']
                },

                # Conflicts and wounds
                "challenges": {
                    "active_conflicts": latest['active_conflicts_count'],
                    "conflict_tension": latest['conflict_tension_level'],
                    "active_wounds": latest['active_wounds_count'],
                    "total_scars": latest['total_scars_count'],
                    "scar_sensitivity": latest['scar_sensitivity_level']
                },

                # Somatic state
                "somatic": {
                    "heart_rate": latest['somatic_heart_rate'],
                    "breath_quality": latest['somatic_breath_quality'],
                    "muscle_tension": latest['somatic_muscle_tension'],
                    "energy_level": latest['somatic_energy_level'],
                    "sensation_summary": latest['somatic_sensation_summary']
                },

                # Trends
                "trends": trends,

                # Summary stats
                "stats": self.data['summary_stats']
            }

    def _calculate_trends(self) -> Dict:
        """Calculate trends by comparing recent time periods"""
        now = datetime.now()
        last_hour_cutoff = now - timedelta(hours=1)
        prev_hour_cutoff = now - timedelta(hours=2)

        last_hour = []
        prev_hour = []

        for snapshot in self.data['snapshots']:
            try:
                timestamp = datetime.fromisoformat(snapshot['timestamp'])
                if timestamp >= last_hour_cutoff:
                    last_hour.append(snapshot)
                elif timestamp >= prev_hour_cutoff:
                    prev_hour.append(snapshot)
            except (KeyError, ValueError):
                continue

        def avg(values: List[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        def trend(current: float, previous: float) -> str:
            diff = current - previous
            if abs(diff) < 0.05:
                return "stable"
            return "increasing" if diff > 0 else "decreasing"

        if not last_hour or not prev_hour:
            return {"status": "insufficient_data"}

        # Calculate averages for both periods
        current_integrity = avg([s['integrity_overall'] for s in last_hour])
        previous_integrity = avg([s['integrity_overall'] for s in prev_hour])

        current_valence = avg([s['overall_valence'] for s in last_hour])
        previous_valence = avg([s['overall_valence'] for s in prev_hour])

        current_cortisol = avg([s['hormonal_cortisol'] for s in last_hour])
        previous_cortisol = avg([s['hormonal_cortisol'] for s in prev_hour])

        current_oxytocin = avg([s['hormonal_oxytocin'] for s in last_hour])
        previous_oxytocin = avg([s['hormonal_oxytocin'] for s in prev_hour])

        return {
            "integrity": {
                "trend": trend(current_integrity, previous_integrity),
                "change": current_integrity - previous_integrity,
                "current_avg": current_integrity
            },
            "valence": {
                "trend": trend(current_valence, previous_valence),
                "change": current_valence - previous_valence,
                "current_avg": current_valence
            },
            "cortisol": {
                "trend": trend(current_cortisol, previous_cortisol),
                "change": current_cortisol - previous_cortisol,
                "current_avg": current_cortisol
            },
            "oxytocin": {
                "trend": trend(current_oxytocin, previous_oxytocin),
                "change": current_oxytocin - previous_oxytocin,
                "current_avg": current_oxytocin
            }
        }

    def _get_integrity_status(self, snapshot: Dict) -> str:
        """Get human-readable integrity status"""
        if snapshot.get('integrity_is_in_crisis'):
            return "crisis"
        elif snapshot.get('integrity_is_vulnerable'):
            return "vulnerable"
        elif snapshot.get('integrity_is_flourishing'):
            return "flourishing"
        else:
            return "stable"

    def _get_dominant_hormone(self, snapshot: Dict) -> str:
        """Get the most elevated hormone"""
        hormones = {
            "oxytocin": snapshot.get('hormonal_oxytocin', 0.3) - 0.3,
            "dopamine": snapshot.get('hormonal_dopamine', 0.4) - 0.4,
            "cortisol": snapshot.get('hormonal_cortisol', 0.2) - 0.2,
            "serotonin": snapshot.get('hormonal_serotonin', 0.5) - 0.5,
            "melatonin": snapshot.get('hormonal_melatonin', 0.3) - 0.3
        }
        return max(hormones, key=hormones.get)

    def get_user_metrics(self, user_id: str) -> Optional[Dict]:
        """
        Get metrics for a specific user.

        Args:
            user_id: The user to get metrics for

        Returns:
            User metrics dictionary or None if not found
        """
        with self._lock:
            return self.data['user_metrics'].get(user_id)

    def get_all_user_summaries(self) -> Dict[str, Dict]:
        """
        Get summaries for all tracked users.

        Returns:
            Dictionary of user_id -> summary
        """
        with self._lock:
            summaries = {}
            for user_id, metrics in self.data['user_metrics'].items():
                summaries[user_id] = {
                    "total_interactions": metrics.get('total_interactions', 0),
                    "last_interaction": metrics.get('last_interaction'),
                    "avg_relational_security": metrics.get('avg_relational_security', 0.5),
                    "avg_valence": metrics.get('avg_valence', 0.0),
                    "dominant_emotion": self._get_top_emotion(metrics.get('dominant_emotions', {}))
                }
            return summaries

    def _get_top_emotion(self, emotions: Dict[str, int]) -> str:
        """Get the most frequent emotion"""
        if not emotions:
            return "unknown"
        return max(emotions, key=emotions.get)

    def get_time_series(self, metric_name: str, hours: int = 24) -> List[Dict]:
        """
        Get a time series for a specific metric.

        Args:
            metric_name: The metric to get (e.g., 'integrity_overall', 'hormonal_cortisol')
            hours: Number of hours of data

        Returns:
            List of {timestamp, value} dictionaries
        """
        with self._lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            series = []

            for snapshot in self.data['snapshots']:
                try:
                    timestamp = datetime.fromisoformat(snapshot['timestamp'])
                    if timestamp >= cutoff and metric_name in snapshot:
                        series.append({
                            "timestamp": snapshot['timestamp'],
                            "value": snapshot[metric_name]
                        })
                except (KeyError, ValueError):
                    continue

            return series

    def get_aggregate_stats(self, hours: int = 24) -> Dict:
        """
        Get aggregate statistics for a time period.

        Args:
            hours: Number of hours to analyze

        Returns:
            Dictionary of aggregate statistics
        """
        with self._lock:
            snapshots = self.get_recent_metrics(hours)

            if not snapshots:
                return {"status": "no_data"}

            def avg(key: str) -> float:
                values = [s[key] for s in snapshots if key in s]
                return sum(values) / len(values) if values else 0.0

            def min_val(key: str) -> float:
                values = [s[key] for s in snapshots if key in s]
                return min(values) if values else 0.0

            def max_val(key: str) -> float:
                values = [s[key] for s in snapshots if key in s]
                return max(values) if values else 0.0

            return {
                "period_hours": hours,
                "snapshot_count": len(snapshots),

                "integrity": {
                    "avg": avg('integrity_overall'),
                    "min": min_val('integrity_overall'),
                    "max": max_val('integrity_overall'),
                    "crisis_periods": sum(1 for s in snapshots if s.get('integrity_is_in_crisis')),
                    "flourishing_periods": sum(1 for s in snapshots if s.get('integrity_is_flourishing'))
                },

                "valence": {
                    "avg": avg('overall_valence'),
                    "min": min_val('overall_valence'),
                    "max": max_val('overall_valence')
                },

                "vulnerability": {
                    "avg": avg('vulnerability_level'),
                    "max": max_val('vulnerability_level')
                },

                "hormonal": {
                    "oxytocin_avg": avg('hormonal_oxytocin'),
                    "dopamine_avg": avg('hormonal_dopamine'),
                    "cortisol_avg": avg('hormonal_cortisol'),
                    "serotonin_avg": avg('hormonal_serotonin'),
                    "melatonin_avg": avg('hormonal_melatonin')
                },

                "conflicts": {
                    "avg_active": avg('active_conflicts_count'),
                    "max_active": max_val('active_conflicts_count'),
                    "avg_tension": avg('conflict_tension_level')
                }
            }

    def _save_async(self):
        """Save data asynchronously to avoid blocking"""
        # For simplicity, we'll save synchronously but could be made async
        # In production, this could use threading or asyncio
        self._save()

    def _save(self):
        """Save telemetry data to disk"""
        try:
            with open(self.data_path, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[Telemetry] Error saving data: {e}")

    def force_save(self):
        """Force immediate save of telemetry data"""
        with self._lock:
            self._save()

    def clear_old_data(self, days: int = 7):
        """
        Clear all data older than specified days.

        Args:
            days: Clear data older than this many days
        """
        with self._lock:
            cutoff = datetime.now() - timedelta(days=days)

            # Filter snapshots
            self.data['snapshots'] = [
                s for s in self.data['snapshots']
                if datetime.fromisoformat(s['timestamp']) >= cutoff
            ]

            # Filter user interaction snapshots
            for user_id in self.data['user_metrics']:
                user_data = self.data['user_metrics'][user_id]
                user_data['recent_snapshots'] = [
                    s for s in user_data.get('recent_snapshots', [])
                    if datetime.fromisoformat(s['timestamp']) >= cutoff
                ]

            self._save()

    def export_data(self) -> Dict:
        """
        Export all telemetry data for backup or analysis.

        Returns:
            Complete telemetry data dictionary
        """
        with self._lock:
            return {
                "exported_at": datetime.now().isoformat(),
                "data": self.data
            }

    def import_data(self, data: Dict, merge: bool = False):
        """
        Import telemetry data.

        Args:
            data: Telemetry data to import
            merge: If True, merge with existing; if False, replace
        """
        with self._lock:
            if merge:
                # Merge snapshots
                self.data['snapshots'].extend(data.get('snapshots', []))

                # Merge user metrics
                for user_id, metrics in data.get('user_metrics', {}).items():
                    if user_id in self.data['user_metrics']:
                        # Merge recent snapshots
                        self.data['user_metrics'][user_id]['recent_snapshots'].extend(
                            metrics.get('recent_snapshots', [])
                        )
                    else:
                        self.data['user_metrics'][user_id] = metrics

                # Sort and deduplicate snapshots
                self.data['snapshots'].sort(key=lambda x: x['timestamp'])
                # Remove duplicates based on timestamp
                seen = set()
                unique = []
                for s in self.data['snapshots']:
                    if s['timestamp'] not in seen:
                        seen.add(s['timestamp'])
                        unique.append(s)
                self.data['snapshots'] = unique

                # Apply retention
                self.data['snapshots'] = self._filter_old_snapshots(self.data['snapshots'])
            else:
                # Replace
                self.data = data

            self._save()

    def to_dict(self) -> dict:
        """Export summary for integration"""
        return {
            "data_path": str(self.data_path),
            "retention_hours": self.retention_hours,
            "snapshot_count": len(self.data['snapshots']),
            "user_count": len(self.data['user_metrics']),
            "summary_stats": self.data['summary_stats'],
            "last_updated": self.data.get('last_updated')
        }
