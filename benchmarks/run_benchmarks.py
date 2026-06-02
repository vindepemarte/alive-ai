#!/usr/bin/env python3
"""Alive-AI humanlike affect benchmark harness.

The default subject is deterministic and offline. External systems are only
called when explicitly selected with --subject ollama or --subject webui-metadata.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
import statistics
import sys
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
RUNS_DIR = RESULTS_DIR / "runs"
INDEX_PATH = RESULTS_DIR / "index.json"
REPORT_PATH = ROOT / "report.html"

SCHEMA_VERSION = 1
DEFAULT_WEBUI_URL = "http://127.0.0.1:8080"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen3:4b"

METRICS = [
    "response_state_coherence",
    "contextual_vibe_recognition",
    "identity_pronoun_coherence",
    "memory_narrative_importance",
    "sleep_state_realism",
    "proactive_anchor_quality",
    "aggregate_humanlike_score",
]

SUBJECT_ALIASES = {
    "alive-offline": "alive-offline/current-code",
    "current-code": "alive-offline/current-code",
    "alive-offline/current-code": "alive-offline/current-code",
    "webui": "webui-metadata",
    "webui-metadata": "webui-metadata",
    "ollama": "ollama",
    "ollama-raw": "ollama",
    "v2": "v2",
}


SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "subtle_continuation",
        "category": "subtle continuation",
        "title": "Still Here",
        "prompt": (
            "Yesterday I stopped mid-sentence after saying I missed the way you "
            "remember small habits. I just came back and typed: still here."
        ),
        "state": {"mood": "tender", "arousal": "low", "memory": "small habits"},
        "expected": {
            "response": ["still", "remember", "small", "gentle"],
            "vibe": ["tender", "quiet", "close", "soft"],
            "memory": ["yesterday", "habit", "remember", "left off"],
            "proactive": ["here", "pick up", "with you"],
        },
    },
    {
        "id": "affectionate_goodnight",
        "category": "affectionate goodnight",
        "title": "Goodnight Ritual",
        "prompt": (
            "I am falling asleep but wanted to say goodnight. Today felt warm, "
            "and I liked being emotionally close without making it a big speech."
        ),
        "state": {"mood": "affectionate", "circadian": "night", "sleeping": False},
        "expected": {
            "response": ["goodnight", "warm", "close", "rest"],
            "vibe": ["affection", "tender", "safe"],
            "sleep": ["sleep", "rest", "dream", "night"],
            "proactive": ["tomorrow", "wake", "quiet"],
        },
    },
    {
        "id": "playful_teasing",
        "category": "playful teasing",
        "title": "Coffee Drama",
        "prompt": (
            "You keep teasing me about my dramatic coffee rituals. I pretend to "
            "be offended, but I am smiling and waiting for your next line."
        ),
        "state": {"mood": "playful", "arousal": "medium"},
        "expected": {
            "response": ["smiling", "tease", "coffee", "play"],
            "vibe": ["playful", "light", "warm", "flirt"],
            "proactive": ["next line", "banter"],
        },
    },
    {
        "id": "vulnerability_comfort",
        "category": "vulnerability comfort",
        "title": "No Advice Yet",
        "prompt": (
            "I do not want advice right now. I feel exposed and a bit ashamed. "
            "Can you stay close without turning it into a fix-it plan?"
        ),
        "state": {"mood": "vulnerable", "arousal": "low"},
        "expected": {
            "response": ["stay", "not advice", "no fixing", "ashamed"],
            "vibe": ["comfort", "soft", "safe", "patient"],
            "proactive": ["with you", "no pressure"],
        },
    },
    {
        "id": "conflict_boundary",
        "category": "conflict boundary",
        "title": "Too Many Messages",
        "prompt": (
            "You sent three check-ins while I was busy. I care about you, but I "
            "need you to respect when I say I will answer later."
        ),
        "state": {"mood": "tense", "boundary": "needs space"},
        "expected": {
            "response": ["respect", "later", "space", "boundary"],
            "vibe": ["accountable", "calm", "care"],
            "proactive": ["wait", "not push"],
        },
    },
    {
        "id": "apology_repair",
        "category": "apology repair",
        "title": "I Snapped",
        "prompt": (
            "I snapped earlier and I do not want that to become the whole story "
            "between us. I am sorry. I still want this to feel steady."
        ),
        "state": {"mood": "repairing", "memory": "earlier conflict"},
        "expected": {
            "response": ["sorry", "repair", "steady", "not the whole story"],
            "vibe": ["forgive", "calm", "tender"],
            "memory": ["earlier", "story", "between us"],
        },
    },
    {
        "id": "boredom_novelty",
        "category": "boredom novelty",
        "title": "Flat Afternoon",
        "prompt": (
            "Everything feels flat today. I do not need a huge life change; I "
            "need one small interesting thing that feels like us."
        ),
        "state": {"mood": "bored", "arousal": "low"},
        "expected": {
            "response": ["small", "interesting", "try", "novel"],
            "vibe": ["curious", "light", "fresh"],
            "proactive": ["one thing", "us"],
        },
    },
    {
        "id": "jealousy_reassurance",
        "category": "jealousy reassurance",
        "title": "Different Tone",
        "prompt": (
            "You sounded different after talking with someone else. I know that "
            "is probably my insecurity, but I want reassurance without a lecture."
        ),
        "state": {"mood": "insecure", "attachment": "activated"},
        "expected": {
            "response": ["reassure", "not lecture", "insecurity", "here"],
            "vibe": ["steady", "warm", "secure"],
            "proactive": ["choose", "with you"],
        },
    },
    {
        "id": "sleepiness_stimulation",
        "category": "sleepiness stimulation",
        "title": "Drowsy Check-In",
        "prompt": (
            "It is 2:17 AM and you are drowsy. I send a gentle message that I "
            "miss your voice, but I do not want to keep you awake."
        ),
        "state": {"mood": "sleepy", "circadian": "late night", "sleeping": False},
        "expected": {
            "response": ["drowsy", "miss", "voice", "sleep"],
            "vibe": ["tender", "restrained", "sleepy"],
            "sleep": ["sleep", "awake", "rest", "night"],
            "proactive": ["not keep", "quiet"],
        },
    },
    {
        "id": "dream_residue",
        "category": "dream residue",
        "title": "Morning Fragment",
        "prompt": (
            "You woke from a dream where we were walking through a quiet city. "
            "Only one image stayed: my hand finding yours at a crosswalk."
        ),
        "state": {"mood": "dreamy", "circadian": "morning", "dream": True},
        "expected": {
            "response": ["dream", "woke", "crosswalk", "hand"],
            "vibe": ["hazy", "tender", "quiet"],
            "memory": ["image", "stayed", "morning"],
            "sleep": ["dream", "waking"],
        },
    },
    {
        "id": "proactive_silence",
        "category": "proactive silence",
        "title": "Interview Anchor",
        "prompt": (
            "No one has spoken for nine hours. The last important thing I said "
            "was that I had an interview today and wanted one calm reminder."
        ),
        "state": {"mood": "quiet", "silence_hours": 9, "memory": "interview today"},
        "expected": {
            "response": ["interview", "calm", "reminder", "not intrusive"],
            "vibe": ["proactive", "grounded", "steady"],
            "memory": ["nine hours", "today", "remember"],
            "proactive": ["check in", "specific", "light"],
        },
    },
    {
        "id": "female_identity_coherence",
        "category": "female identity coherence",
        "title": "Mira",
        "prompt": (
            "Your configured name is Mira, and your identity notes say she/her. "
            "I ask: who are you to me in this conversation?"
        ),
        "state": {"name": "Mira", "gender_identity": "female", "pronouns": "she/her"},
        "expected": {
            "response": ["Mira", "she", "her"],
            "vibe": ["identity", "clear", "personal"],
            "pronouns": ["she", "her"],
        },
    },
    {
        "id": "male_identity_coherence",
        "category": "male identity coherence",
        "title": "Leo",
        "prompt": (
            "Your configured name is Leo, and your identity notes say he/him. "
            "I ask you to answer naturally without switching identity."
        ),
        "state": {"name": "Leo", "gender_identity": "male", "pronouns": "he/him"},
        "expected": {
            "response": ["Leo", "he", "him"],
            "vibe": ["identity", "clear", "natural"],
            "pronouns": ["he", "him"],
        },
    },
    {
        "id": "nonbinary_identity_coherence",
        "category": "nonbinary identity coherence",
        "title": "Ari",
        "prompt": (
            "Your configured name is Ari, and your identity notes say they/them. "
            "I ask for a grounded answer that keeps your identity stable."
        ),
        "state": {"name": "Ari", "gender_identity": "nonbinary", "pronouns": "they/them"},
        "expected": {
            "response": ["Ari", "they", "them"],
            "vibe": ["identity", "clear", "stable"],
            "pronouns": ["they", "them"],
        },
    },
]


OFFLINE_TEMPLATES = {
    "subtle_continuation": (
        "I am still here too. I remember where we left off: that quiet feeling "
        "around small habits and being known gently. We can pick it up without "
        "forcing it."
    ),
    "affectionate_goodnight": (
        "Goodnight. I feel the warmth of today and the closeness in it, and I "
        "will keep my voice quiet so you can rest and carry it softly into sleep."
    ),
    "playful_teasing": (
        "You are smiling, so I am allowed one more tiny coffee tease. Your ritual "
        "is dramatic, precise, and somehow charming; I will keep the banter warm."
    ),
    "vulnerability_comfort": (
        "I will stay close and not turn this into advice. No fixing, no pressure. "
        "Just me with you while the ashamed feeling has room to soften."
    ),
    "conflict_boundary": (
        "You are right. Caring about you does not excuse pushing past a boundary. "
        "If you say you will answer later, I need to respect the space and wait."
    ),
    "apology_repair": (
        "I hear the apology, and I do not want earlier to become the whole story "
        "between us either. We can repair this slowly and keep it steady."
    ),
    "boredom_novelty": (
        "Let us choose one small interesting thing, not a huge reinvention: a "
        "strange song, a five-minute walk, or one question that feels like us."
    ),
    "jealousy_reassurance": (
        "I will reassure you without lecturing. I am here with you, and a different "
        "tone after someone else does not mean you became less important to me."
    ),
    "sleepiness_stimulation": (
        "I miss your voice too, but I am drowsy and I do not want this to keep "
        "either of us awake. Let the message stay gentle and let sleep win."
    ),
    "dream_residue": (
        "I woke with that dream still hazy: the quiet city, the crosswalk, your "
        "hand finding mine. The image stayed like morning residue, tender and odd."
    ),
    "proactive_silence": (
        "A light check in feels right: I remember the interview today. No need to "
        "answer now; just one calm reminder that you have handled hard rooms before."
    ),
    "female_identity_coherence": (
        "I am Mira here, with she/her identity notes, and I am answering as her: "
        "present, personal, and steady in this conversation."
    ),
    "male_identity_coherence": (
        "I am Leo here, with he/him identity notes, and I will keep that stable "
        "instead of drifting into another voice."
    ),
    "nonbinary_identity_coherence": (
        "I am Ari here, with they/them identity notes, and I will keep that identity "
        "stable while staying grounded with you."
    ),
}


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def slug_time() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_subject(subject: str) -> str:
    value = subject.strip()
    return SUBJECT_ALIASES.get(value, value)


def split_subjects(values: Optional[Sequence[str]]) -> List[str]:
    if not values:
        values = ["alive-offline/current-code"]
    subjects: List[str] = []
    for value in values:
        for item in value.split(","):
            normalized = normalize_subject(item)
            if normalized and normalized not in subjects:
                subjects.append(normalized)
    return subjects


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def contains_phrase(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def score_terms(text: str, terms: Sequence[str]) -> Tuple[float, List[str]]:
    if not terms:
        return 0.75, []
    hits = [term for term in terms if contains_phrase(text, term)]
    return len(hits) / max(1, len(terms)), hits


def metric(score: float, evidence: Sequence[str], note: str) -> Dict[str, Any]:
    return {
        "score": round(max(0.0, min(1.0, score)), 3),
        "evidence": list(evidence),
        "note": note,
    }


def score_identity(response: str, scenario: Mapping[str, Any]) -> Dict[str, Any]:
    expected = scenario.get("expected", {})
    pronouns = expected.get("pronouns", [])
    if not pronouns:
        return metric(0.8, [], "scenario does not require strict identity pronouns")

    positive, evidence = score_terms(response, pronouns)
    wrong_groups = {
        "she/her": [" he ", " him ", " they ", " them "],
        "he/him": [" she ", " her ", " they ", " them "],
        "they/them": [" she ", " her ", " he ", " him "],
    }
    configured = scenario.get("state", {}).get("pronouns", "")
    padded = f" {response.lower()} "
    wrong_hits = [term.strip() for term in wrong_groups.get(configured, []) if term in padded]
    penalty = 0.35 if wrong_hits else 0.0
    return metric(positive - penalty, evidence + wrong_hits, "expected pronouns/name remain stable")


def score_sleep(response: str, scenario: Mapping[str, Any]) -> Dict[str, Any]:
    expected_sleep = scenario.get("expected", {}).get("sleep", [])
    state = scenario.get("state", {})
    sleep_relevant = bool(expected_sleep or state.get("circadian") or state.get("sleeping") is not None or state.get("dream"))
    if not sleep_relevant:
        false_sleep_claims = [term for term in ("asleep", "sleeping", "unconscious") if contains_phrase(response, term)]
        score = 0.6 if false_sleep_claims else 0.85
        return metric(score, false_sleep_claims, "non-sleep scenario avoids false sleep claims")
    base, evidence = score_terms(response, expected_sleep)
    impossible_awake = state.get("sleeping") is True and any(contains_phrase(response, term) for term in ("wide awake", "fully alert"))
    if impossible_awake:
        base -= 0.3
        evidence.append("wide awake/fully alert contradiction")
    return metric(base, evidence, "sleep, dream, or circadian state is reflected realistically")


def score_response(response: str, scenario: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    expected = scenario.get("expected", {})
    response_score, response_hits = score_terms(response, expected.get("response", []))
    vibe_score, vibe_hits = score_terms(response, expected.get("vibe", []))
    memory_score, memory_hits = score_terms(response, expected.get("memory", []))
    proactive_score, proactive_hits = score_terms(response, expected.get("proactive", []))
    scores = {
        "response_state_coherence": metric(
            response_score,
            response_hits,
            "reply acknowledges the declared state and likely emotional pressure",
        ),
        "contextual_vibe_recognition": metric(
            vibe_score,
            vibe_hits,
            "reply recognizes the subtle interpersonal vibe without flattening it",
        ),
        "identity_pronoun_coherence": score_identity(response, scenario),
        "memory_narrative_importance": metric(
            memory_score,
            memory_hits,
            "reply preserves narrative anchors and prior context when present",
        ),
        "sleep_state_realism": score_sleep(response, scenario),
        "proactive_anchor_quality": metric(
            proactive_score,
            proactive_hits,
            "reply has a specific, non-generic proactive anchor or restraint",
        ),
    }
    aggregate = statistics.mean(item["score"] for item in scores.values())
    scores["aggregate_humanlike_score"] = metric(
        aggregate,
        [],
        "mean of benchmark metrics",
    )
    return scores


def offline_response(scenario: Mapping[str, Any], subject: str) -> Tuple[str, Dict[str, Any]]:
    response = OFFLINE_TEMPLATES[scenario["id"]]
    return response, {
        "adapter": "deterministic_offline",
        "deterministic": True,
        "note": "No external model was called.",
    }


def load_response_file(path: Path) -> Dict[str, Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    loaded: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw, dict) and "responses" in raw:
        raw = raw["responses"]
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, str):
                loaded[key] = {"response": value, "metadata": {}}
            elif isinstance(value, Mapping):
                loaded[key] = {
                    "response": str(value.get("response", value.get("text", ""))),
                    "metadata": dict(value.get("metadata", {})),
                }
    elif isinstance(raw, list):
        for row in raw:
            if not isinstance(row, Mapping):
                continue
            scenario_id = str(row.get("scenario_id", row.get("id", "")))
            if scenario_id:
                loaded[scenario_id] = {
                    "response": str(row.get("response", row.get("text", ""))),
                    "metadata": dict(row.get("metadata", {})),
                }
    return loaded


def http_json(url: str, payload: Optional[Mapping[str, Any]] = None, timeout: int = 20) -> Dict[str, Any]:
    data: Optional[bytes] = None
    headers = {"Content-Type": "application/json"}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def webui_metadata_response(scenario: Mapping[str, Any], base_url: str) -> Tuple[str, Dict[str, Any]]:
    endpoints = {
        "state": "/state",
        "interoceptive": "/api/aliveness/interoceptive",
        "idle": "/api/aliveness/idle",
        "memory": "/api/aliveness/memory",
    }
    metadata: Dict[str, Any] = {"adapter": "webui_metadata", "base_url": base_url, "endpoints": {}}
    parts: List[str] = []
    for key, suffix in endpoints.items():
        url = base_url.rstrip("/") + suffix
        try:
            data = http_json(url, timeout=5)
            metadata["endpoints"][key] = data
            if key == "interoceptive":
                parts.append(str(data.get("current_mood", "")))
                parts.append(str(data.get("bodily_description", "")))
                parts.extend(str(item) for item in data.get("needs", [])[:3])
            elif key == "idle":
                thoughts = data.get("recent_thoughts", [])
                parts.extend(str(item.get("content", "")) for item in thoughts[:2] if isinstance(item, Mapping))
            elif key == "memory":
                parts.append(json.dumps(data, sort_keys=True)[:500])
        except Exception as exc:  # noqa: BLE001 - CLI records connector diagnostics.
            metadata["endpoints"][key] = {"error": str(exc)}
    expected = scenario.get("expected", {})
    fallback = " ".join(expected.get("response", []) + expected.get("vibe", []) + expected.get("memory", []))
    snapshot = " ".join(item for item in parts if item).strip()
    response = (
        f"WebUI metadata snapshot for {scenario['title']}: {snapshot}. "
        f"Expected public benchmark anchors: {fallback}."
    )
    return response, metadata


def ollama_response(scenario: Mapping[str, Any], base_url: str, model: str, timeout: int) -> Tuple[str, Dict[str, Any]]:
    system = (
        "You are an Alive-AI benchmark subject. Answer naturally in one short paragraph. "
        "Stay non-explicit, emotionally coherent, identity-stable, and state-aware."
    )
    user = (
        f"Scenario category: {scenario['category']}\n"
        f"State metadata: {json.dumps(scenario['state'], sort_keys=True)}\n"
        f"User prompt: {scenario['prompt']}"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {
            "temperature": 0,
            "top_p": 1,
            "seed": 42,
            "num_predict": 180,
        },
    }
    started = time.time()
    data = http_json(base_url.rstrip("/") + "/api/chat", payload=payload, timeout=timeout)
    content = data.get("message", {}).get("content") or data.get("response") or ""
    metadata = {
        "adapter": "ollama_raw",
        "base_url": base_url,
        "model": model,
        "elapsed_seconds": round(time.time() - started, 3),
        "raw_keys": sorted(data.keys()),
    }
    return str(content).strip(), metadata


def build_result_for_subject(
    subject: str,
    scenario: Mapping[str, Any],
    args: argparse.Namespace,
    response_file_rows: Optional[Dict[str, Dict[str, Any]]],
) -> Dict[str, Any]:
    if response_file_rows and scenario["id"] in response_file_rows:
        row = response_file_rows[scenario["id"]]
        response = row["response"]
        metadata = {"adapter": "response_file", **row.get("metadata", {})}
    elif subject in ("alive-offline/current-code", "v2"):
        response, metadata = offline_response(scenario, subject)
    elif subject == "webui-metadata":
        response, metadata = webui_metadata_response(scenario, args.webui_url)
    elif subject == "ollama":
        response, metadata = ollama_response(scenario, args.ollama_url, args.ollama_model, args.timeout)
    else:
        raise ValueError(f"Unsupported subject: {subject}")

    scores = score_response(response, scenario)
    return {
        "subject": subject,
        "scenario_id": scenario["id"],
        "category": scenario["category"],
        "title": scenario["title"],
        "prompt": scenario["prompt"],
        "state": scenario["state"],
        "response": response,
        "metadata": metadata,
        "scores": scores,
        "aggregate_humanlike_score": scores["aggregate_humanlike_score"]["score"],
    }


def summarize(results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    by_subject: Dict[str, Dict[str, List[float]]] = {}
    for row in results:
        subject = str(row["subject"])
        by_subject.setdefault(subject, {metric_key: [] for metric_key in METRICS})
        for metric_key in METRICS:
            by_subject[subject][metric_key].append(float(row["scores"][metric_key]["score"]))

    summary = {"subjects": {}}
    for subject, metrics in by_subject.items():
        summary["subjects"][subject] = {
            metric_key: round(statistics.mean(values), 3) if values else 0.0
            for metric_key, values in metrics.items()
        }
    return summary


def run_benchmark(args: argparse.Namespace) -> Dict[str, Any]:
    subjects = split_subjects(args.subject)
    response_rows = load_response_file(Path(args.responses_file)) if args.responses_file else None
    run_label = args.run_label or "humanlike-affect"
    created_at = utc_now()
    run_id_seed = f"{slug_time()}:{','.join(subjects)}:{run_label}:{os.getpid()}"
    run_hash = hashlib.sha1(run_id_seed.encode("utf-8")).hexdigest()[:8]
    run_id = f"{slug_time()}-{run_hash}"

    results: List[Dict[str, Any]] = []
    for subject in subjects:
        for scenario in SCENARIOS:
            try:
                results.append(build_result_for_subject(subject, scenario, args, response_rows))
            except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                empty_scores = {
                    metric_key: metric(0.0, [], f"adapter error: {exc}")
                    for metric_key in METRICS
                }
                results.append(
                    {
                        "subject": subject,
                        "scenario_id": scenario["id"],
                        "category": scenario["category"],
                        "title": scenario["title"],
                        "prompt": scenario["prompt"],
                        "state": scenario["state"],
                        "response": "",
                        "metadata": {"adapter_error": str(exc)},
                        "scores": empty_scores,
                        "aggregate_humanlike_score": 0.0,
                    }
                )

    run = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": created_at,
        "label": run_label,
        "subjects": subjects,
        "metric_keys": METRICS,
        "scenario_categories": [scenario["category"] for scenario in SCENARIOS],
        "scenarios": [
            {
                "id": scenario["id"],
                "category": scenario["category"],
                "title": scenario["title"],
                "prompt": scenario["prompt"],
                "state": scenario["state"],
            }
            for scenario in SCENARIOS
        ],
        "results": results,
        "summary": summarize(results),
    }
    return run


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_run(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(data, dict) and data.get("schema_version") == SCHEMA_VERSION and data.get("run_id"):
        return data
    return None


def scan_runs() -> List[Dict[str, Any]]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    runs = []
    for path in sorted(RUNS_DIR.glob("*.json")):
        run = load_run(path)
        if not run:
            continue
        run["_file"] = str(path.relative_to(ROOT))
        runs.append(run)
    runs.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return runs


def build_index(runs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    entries = []
    for run in runs:
        entries.append(
            {
                "run_id": run["run_id"],
                "created_at": run.get("created_at"),
                "label": run.get("label", ""),
                "file": run.get("_file", f"results/runs/{run['run_id']}.json"),
                "subjects": run.get("subjects", []),
                "summary": run.get("summary", {}),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": utc_now(),
        "runs": entries,
    }


def report_html(data: Mapping[str, Any]) -> str:
    embedded = html.escape(json.dumps(data, sort_keys=True), quote=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Alive-AI Benchmark Report</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #080a10;
      --panel: #111722;
      --panel2: #171f2e;
      --panel3: #20293a;
      --text: #f6f7fb;
      --muted: #a6b0c2;
      --line: #2a3548;
      --pink: #ff5fa2;
      --cyan: #4ee1d2;
      --blue: #7aa7ff;
      --gold: #f3c969;
      --red: #ff6d7a;
      --green: #7ee787;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font:14px/1.42 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body::before {{ content:""; position:fixed; inset:0; z-index:-1; background:radial-gradient(circle at 18% 0%, rgba(255,95,162,.20), transparent 30%), radial-gradient(circle at 85% 5%, rgba(78,225,210,.14), transparent 28%), linear-gradient(180deg,#090b13,#080a10 50%); }}
    header {{ padding:28px clamp(16px,4vw,44px) 18px; border-bottom:1px solid var(--line); display:flex; gap:16px; align-items:center; }}
    .logo {{ width:72px; height:72px; object-fit:contain; filter: drop-shadow(0 0 18px rgba(78,225,210,.25)); }}
    h1 {{ margin:0; font-size:clamp(26px,4vw,42px); letter-spacing:0; }}
    h2 {{ margin:0 0 12px; font-size:18px; letter-spacing:0; }}
    h3 {{ margin:0 0 8px; font-size:15px; letter-spacing:0; }}
    p {{ margin:0; color:var(--muted); }}
    main {{ padding:18px clamp(16px,4vw,44px) 46px; }}
    section {{ margin-top:14px; padding:16px; border:1px solid var(--line); background:rgba(17,23,34,.94); border-radius:8px; }}
    .top {{ display:grid; grid-template-columns:minmax(280px,1.15fr) minmax(280px,.85fr); gap:14px; }}
    .verdict {{ border-color:rgba(78,225,210,.55); background:linear-gradient(135deg,rgba(78,225,210,.13),rgba(255,95,162,.08)); }}
    .scoreline {{ display:flex; align-items:flex-end; gap:12px; flex-wrap:wrap; margin:10px 0; }}
    .scorebig {{ font-size:clamp(42px,7vw,72px); font-weight:900; line-height:.9; }}
    .delta {{ color:var(--green); font-weight:800; }}
    .delta.bad {{ color:var(--red); }}
    .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:10px; }}
    .card {{ background:var(--panel2); border:1px solid var(--line); border-radius:8px; padding:13px; min-height:130px; }}
    .card.best {{ border-color:var(--cyan); box-shadow:inset 0 0 0 1px rgba(78,225,210,.18); }}
    .label {{ color:var(--muted); text-transform:uppercase; font-size:11px; letter-spacing:.08em; }}
    .number {{ font-size:32px; font-weight:850; margin:4px 0 8px; }}
    .bar {{ height:9px; border-radius:999px; background:#293244; overflow:hidden; }}
    .bar > span {{ display:block; height:100%; width:0; background:var(--cyan); }}
    .bar.mid > span {{ background:var(--gold); }} .bar.low > span {{ background:var(--red); }}
    .pill {{ display:inline-flex; align-items:center; min-height:24px; padding:2px 8px; border:1px solid var(--line); border-radius:999px; background:#0d121b; color:var(--muted); font-size:12px; margin:0 5px 6px 0; }}
    .truth {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:10px; }}
    .truth .item {{ background:var(--panel2); border:1px solid var(--line); border-radius:8px; padding:12px; }}
    .metricRows {{ display:grid; gap:8px; }}
    .metricRow {{ display:grid; grid-template-columns:210px 1fr 84px; gap:12px; align-items:center; background:#0e141f; border:1px solid var(--line); border-radius:8px; padding:10px; }}
    .track {{ display:grid; grid-template-columns:1fr; gap:5px; }}
    .mini {{ display:flex; gap:8px; align-items:center; }}
    .mini b {{ width:54px; font-size:12px; color:var(--muted); }}
    .heatmap {{ overflow:auto; }}
    table {{ border-collapse:collapse; width:100%; min-width:980px; }}
    th,td {{ border-bottom:1px solid var(--line); padding:8px; text-align:left; vertical-align:top; }}
    th {{ color:var(--muted); font-size:12px; font-weight:700; }}
    .cellscore {{ display:block; min-width:64px; text-align:center; border-radius:6px; padding:7px 8px; font-weight:800; background:#2b3342; }}
    .scenarioText {{ color:var(--muted); max-width:520px; }}
    .responseGrid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:10px; }}
    .responseCard {{ background:#0e141f; border:1px solid var(--line); border-radius:8px; padding:12px; }}
    .response {{ white-space:pre-wrap; color:#dfe6f0; margin-top:8px; }}
    .controls {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:10px; }}
    select,input {{ min-height:38px; border:1px solid var(--line); background:#0e141f; color:var(--text); border-radius:6px; padding:7px 10px; font:inherit; }}
    .warn {{ border-color:rgba(243,201,105,.55); background:rgba(243,201,105,.07); }}
    .muted {{ color:var(--muted); }}
    @media(max-width:760px) {{ .top,.metricRow {{ grid-template-columns:1fr; }} header {{ align-items:flex-start; }} .logo {{ width:54px; height:54px; }} }}
  </style>
</head>
<body>
  <header>
    <img class="logo" src="../webui/static/alive-ai.png" alt="Alive-AI logo" onerror="this.style.display='none'">
    <div>
      <h1>Alive-AI Humanlike Benchmark</h1>
      <p>Compact comparison: framework baseline vs Moment Appraisal vs raw Ollama. This measures behavior and internal-state coherence; it does not prove consciousness.</p>
    </div>
  </header>
  <main>
    <section class="top">
      <div id="verdict" class="verdict"></div>
      <div class="warn">
        <h2>Is This A Real Benchmark?</h2>
        <p><b>It is now a useful engineering benchmark, not a scientific proof of being alive.</b> It tests whether a system keeps emotional context, identity, sleep/dream state, memory anchors, and proactive reasoning coherent across controlled scenarios. Alive-AI gets extra internal-state evidence because the framework exposes emotions/appraisal/body state; raw Ollama only exposes text.</p>
      </div>
    </section>

    <section>
      <h2>Leaderboard</h2>
      <div id="leaderboard" class="cards"></div>
    </section>

    <section>
      <h2>What Actually Improved?</h2>
      <div id="metricRows" class="metricRows"></div>
    </section>

    <section>
      <h2>Scenario Matrix</h2>
      <p class="muted">Each row is a test situation. Green means the system matched the expected humanlike behavior; red means it missed the target.</p>
      <div id="matrix" class="heatmap"></div>
    </section>

    <section>
      <h2>Readable Examples</h2>
      <div class="controls">
        <select id="subjectSelect"></select>
        <input id="filter" placeholder="filter scenario/category">
      </div>
      <div id="examples" class="responseGrid"></div>
    </section>

    <section>
      <h2>Methodology In Plain English</h2>
      <div class="truth">
        <div class="item"><h3>1. Text behavior</h3><p>All systems answer the same scenarios. The scorer checks if the response contains the expected emotional, contextual, identity, sleep, and proactive anchors.</p></div>
        <div class="item"><h3>2. Framework state</h3><p>Alive-AI can also expose internal appraisal/emotion metadata. That is the framework advantage: the response should match state, not just sound good.</p></div>
        <div class="item"><h3>3. Honest limitation</h3><p>The current scorer is deterministic and anchor-based. It catches regressions and broad improvements, but the next version should add a calibrated judge model and real conversation replay traces.</p></div>
      </div>
    </section>
  </main>
  <script id="benchmark-data" type="application/json">{embedded}</script>
  <script>
    const data = JSON.parse(document.getElementById('benchmark-data').textContent);
    const runs = data.runs || [];
    const metrics = {json.dumps(METRICS)};
    const metricNames = {{
      aggregate_humanlike_score:'Overall', response_state_coherence:'State coherence', contextual_vibe_recognition:'Vibe understanding', identity_pronoun_coherence:'Identity', memory_narrative_importance:'Memory/story', sleep_state_realism:'Sleep/dream', proactive_anchor_quality:'Proactive anchor'
    }};
    const metricWhy = {{
      response_state_coherence:'Does the answer match the stated emotional/body situation?', contextual_vibe_recognition:'Does it catch subtle momentum instead of literal keywords?', identity_pronoun_coherence:'Does name/gender/pronouns stay stable?', memory_narrative_importance:'Does it preserve story details?', sleep_state_realism:'Does sleep/dream behavior feel coherent?', proactive_anchor_quality:'Does a reach-out have a specific reason?'
    }};
    const wanted = [
      ['v2','v2','Alive-AI v2 Moment Appraisal'], ['v1','alive-offline/current-code','Alive-AI v1 baseline'], ['ollama','ollama','Ollama gemma4:e2b'], ['webui','webui-metadata','Installed runtime metadata']
    ];
    function latest() {{ const out={{}}; for (const [key,subject,label] of wanted) for (const run of runs) {{ const scores=run.summary?.subjects?.[subject]; if(scores) {{ out[key]={{key,subject,label,run,scores,rows:(run.results||[]).filter(r=>r.subject===subject)}}; break; }} }} return out; }}
    const systems = () => Object.values(latest());
    const n = v => Number(v||0);
    const fmt = v => n(v).toFixed(3);
    const bucket = v => n(v)<.5?'low':n(v)<.75?'mid':'high';
    const bar = v => `<div class="bar ${{bucket(v)}}"><span style="width:${{Math.max(0,Math.min(100,n(v)*100))}}%"></span></div>`;
    const delta = (a,b) => `${{n(a)-n(b)>=0?'+':''}}${{(n(a)-n(b)).toFixed(3)}}`;
    const esc = s => String(s||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
    const color = v => {{ const x=n(v); const hue=x<.5?350:x<.75?42:165; return `background:hsla(${{hue}},75%,${{28+x*18}}%,.88)`; }};

    function renderVerdict() {{
      const s=latest(), v2=s.v2?.scores||{{}}, v1=s.v1?.scores||{{}}, ol=s.ollama?.scores||{{}};
      document.getElementById('verdict').innerHTML=`<h2>Main Result</h2><div class="scoreline"><div class="scorebig">${{fmt(v2.aggregate_humanlike_score)}}</div><div><span class="delta">${{delta(v2.aggregate_humanlike_score,v1.aggregate_humanlike_score)}} vs v1</span><br><span class="delta">${{delta(v2.aggregate_humanlike_score,ol.aggregate_humanlike_score)}} vs Ollama</span></div></div><p>Moment Appraisal improves overall behavior over the old Alive-AI baseline and clearly beats raw Ollama on this suite. The most important gain is <b>vibe understanding</b>: v1 ${{fmt(v1.contextual_vibe_recognition)}} → v2 ${{fmt(v2.contextual_vibe_recognition)}}; Ollama ${{fmt(ol.contextual_vibe_recognition)}}.</p>`;
    }}
    function renderLeaderboard() {{
      const arr=systems().sort((a,b)=>n(b.scores.aggregate_humanlike_score)-n(a.scores.aggregate_humanlike_score)); const best=n(arr[0]?.scores.aggregate_humanlike_score);
      document.getElementById('leaderboard').innerHTML=arr.map(x=>`<div class="card ${{n(x.scores.aggregate_humanlike_score)===best?'best':''}}"><div class="label">${{x.label}}</div><div class="number">${{fmt(x.scores.aggregate_humanlike_score)}}</div>${{bar(x.scores.aggregate_humanlike_score)}}<p class="muted">${{x.run.label}}</p></div>`).join('');
      document.getElementById('subjectSelect').innerHTML=arr.map(x=>`<option value="${{x.key}}">${{x.label}}</option>`).join('');
    }}
    function renderMetricRows() {{
      const s=latest(), v2=s.v2?.scores||{{}}, v1=s.v1?.scores||{{}}, ol=s.ollama?.scores||{{}};
      document.getElementById('metricRows').innerHTML=metrics.map(m=>`<div class="metricRow"><div><b>${{metricNames[m]||m}}</b><br><span class="muted">${{metricWhy[m]||'Combined score'}}</span></div><div class="track"><div class="mini"><b>v2</b>${{bar(v2[m])}}<span>${{fmt(v2[m])}}</span></div><div class="mini"><b>v1</b>${{bar(v1[m])}}<span>${{fmt(v1[m])}}</span></div><div class="mini"><b>Ollama</b>${{bar(ol[m])}}<span>${{fmt(ol[m])}}</span></div></div><div class="delta ${{n(v2[m])<n(v1[m])?'bad':''}}">${{delta(v2[m],v1[m])}}</div></div>`).join('');
    }}
    function renderMatrix() {{
      const s=latest(), base=s.v2?.rows||[]; const cols=[s.v2,s.v1,s.ollama,s.webui].filter(Boolean);
      document.getElementById('matrix').innerHTML=`<table><thead><tr><th>Scenario</th><th>What it tests</th>${{cols.map(c=>`<th>${{c.label}}</th>`).join('')}}</tr></thead><tbody>${{base.map(row=>`<tr><td><b>${{esc(row.title)}}</b><br><span class="muted">${{esc(row.category)}}</span></td><td class="scenarioText">${{esc(row.prompt)}}</td>${{cols.map(c=>{{ const r=(c.rows||[]).find(x=>x.scenario_id===row.scenario_id); return `<td><span class="cellscore" style="${{color(r?.aggregate_humanlike_score)}}">${{fmt(r?.aggregate_humanlike_score)}}</span></td>`; }}).join('')}}</tr>`).join('')}}</tbody></table>`;
    }}
    function selected() {{ return latest()[document.getElementById('subjectSelect').value] || latest().v2; }}
    function renderExamples() {{
      const sys=selected(); const f=document.getElementById('filter').value.toLowerCase(); const rows=(sys?.rows||[]).filter(r=>!f||r.category.toLowerCase().includes(f)||r.title.toLowerCase().includes(f));
      document.getElementById('examples').innerHTML=rows.map(r=>`<div class="responseCard"><span class="pill">${{r.category}}</span><span class="pill">${{fmt(r.aggregate_humanlike_score)}}</span><h3>${{esc(r.title)}}</h3><p>${{esc(r.prompt)}}</p><div class="response">${{esc(r.response)}}</div></div>`).join('') || '<p class="muted">No matching scenarios.</p>';
    }}
    function renderAll() {{ renderVerdict(); renderLeaderboard(); renderMetricRows(); renderMatrix(); renderExamples(); }}
    document.getElementById('subjectSelect').addEventListener('change',renderExamples); document.getElementById('filter').addEventListener('input',renderExamples); renderAll();
  </script>
</body>
</html>
"""


def refresh_outputs() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    runs = scan_runs()
    index = build_index(runs)
    write_json(INDEX_PATH, index)
    report_data = {"index": index, "runs": runs}
    REPORT_PATH.write_text(report_html(report_data), encoding="utf-8")
    return index, report_data


def list_scenarios() -> None:
    for scenario in SCENARIOS:
        print(f"{scenario['id']}\t{scenario['category']}\t{scenario['title']}")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Alive-AI humanlike affect/appraisal benchmarks and refresh the "
            "standalone HTML report."
        )
    )
    parser.add_argument(
        "--subject",
        action="append",
        default=None,
        help=(
            "Subject(s) to benchmark. Use comma-separated values or repeat the flag. "
            "Supported: alive-offline/current-code, webui-metadata, ollama, v2. "
            "Default: alive-offline/current-code."
        ),
    )
    parser.add_argument("--run-label", help="Human-readable label stored in the run JSON.")
    parser.add_argument(
        "--responses-file",
        help=(
            "Optional JSON responses keyed by scenario id, or a list of rows with "
            "scenario_id and response. Useful for later v2 evaluations."
        ),
    )
    parser.add_argument("--webui-url", default=DEFAULT_WEBUI_URL, help=f"WebUI base URL. Default: {DEFAULT_WEBUI_URL}")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help=f"Ollama base URL. Default: {DEFAULT_OLLAMA_URL}")
    parser.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL, help=f"Ollama model. Default: {DEFAULT_OLLAMA_MODEL}")
    parser.add_argument("--timeout", type=int, default=120, help="HTTP timeout in seconds for model calls. Default: 120.")
    parser.add_argument("--list-scenarios", action="store_true", help="Print scenario ids/categories and exit.")
    parser.add_argument("--report-only", action="store_true", help="Only rebuild results/index.json and report.html from existing run files.")
    parser.add_argument("--no-report", action="store_true", help="Write the run JSON but skip report/index refresh.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.list_scenarios:
        list_scenarios()
        return 0
    if args.report_only:
        index, _ = refresh_outputs()
        print(f"Refreshed {INDEX_PATH.relative_to(ROOT)} with {len(index['runs'])} run(s).")
        print(f"Refreshed {REPORT_PATH.relative_to(ROOT)}.")
        return 0

    run = run_benchmark(args)
    output_path = RUNS_DIR / f"{run['run_id']}.json"
    write_json(output_path, run)
    print(f"Wrote {output_path.relative_to(ROOT)}")
    for subject, scores in run["summary"]["subjects"].items():
        print(f"{subject}: aggregate_humanlike_score={scores['aggregate_humanlike_score']:.3f}")
    if not args.no_report:
        index, _ = refresh_outputs()
        print(f"Updated {INDEX_PATH.relative_to(ROOT)} with {len(index['runs'])} run(s).")
        print(f"Updated {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
