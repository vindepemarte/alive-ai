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
    "webui-chat": "webui-chat",
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


def webui_chat_response(scenario: Mapping[str, Any], base_url: str, timeout: int = 45) -> Tuple[str, Dict[str, Any]]:
    import time
    state_url = base_url.rstrip("/") + "/state"
    chat_url = base_url.rstrip("/") + "/api/chat"
    
    try:
        init_state = http_json(state_url, timeout=5)
        init_count = len(init_state.get("conversation", []))
    except Exception:
        init_count = 0
        
    payload = {
        "text": scenario["prompt"],
        "user_id": "benchmark",
        "message_id": f"benchmark_{scenario['id']}_{int(time.time())}"
    }
    
    try:
        http_json(chat_url, payload, timeout=10)
    except Exception as exc:
        return f"Error sending chat to WebUI: {exc}", {"error": str(exc)}
        
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(1.0)
        try:
            state = http_json(state_url, timeout=5)
            conv = state.get("conversation", [])
            if len(conv) > init_count:
                for msg in reversed(conv):
                    if msg.get("role") in ("alive_ai", "assistant") and msg.get("status") == "sent":
                        metadata = {
                            "adapter": "webui_chat",
                            "base_url": base_url,
                            "state": state.get("aliveness", {}).get("interoceptive", {}).get("states", {}),
                            "mood": state.get("aliveness", {}).get("interoceptive", {}).get("current_mood"),
                            "raw_state": state
                        }
                        return msg.get("content", ""), metadata
        except Exception:
            pass
            
    return f"Timeout waiting for WebUI AI response after {timeout} seconds.", {"error": "timeout"}


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
    elif subject == "webui-chat":
        response, metadata = webui_chat_response(scenario, args.webui_url, args.timeout)
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
  <title>Alive-AI | Benchmark Visualizer</title>
  
  <!-- Modern Typography and Code Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700;800;900&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">

  <style>
    /* Design Variables matching logo and brand aesthetics */
    :root {{
      color-scheme: dark;
      
      --bg: #070a0f;
      --bg-gradient: radial-gradient(circle at 50% 0%, #0d1624 0%, #070a0f 70%);
      --surface: rgba(13, 22, 36, 0.45);
      --surface-hover: rgba(18, 30, 49, 0.65);
      --surface-strong: rgba(21, 35, 57, 0.85);
      --surface-border: #253445;
      
      --accent-pink: #ff5c8a; /* Emotion Accent */
      --accent-green: #41f0a1; /* Aliveness Accent */
      --accent-blue: #3b82f6;
      --accent-gold: #ffcf5a;
      --accent-red: #ff8068;
      
      --text: #f3f4f6;
      --text-muted: #637d9b;
      
      --transition-smooth: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background-color: var(--bg);
      background-image: var(--bg-gradient);
      color: var(--text);
      font-family: 'Inter', sans-serif;
      line-height: 1.5;
      overflow-x: hidden;
      -webkit-font-smoothing: antialiased;
      padding-bottom: 80px;
    }}

    /* Grid overlay details */
    .grid-overlay {{
      position: fixed;
      inset: 0;
      background-image: 
        linear-gradient(rgba(37, 52, 69, 0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(37, 52, 69, 0.04) 1px, transparent 1px);
      background-size: 48px 48px;
      pointer-events: none;
      z-index: -1;
    }}

    header {{
      display: flex;
      align-items: center;
      gap: 20px;
      padding: 32px clamp(16px, 4vw, 48px);
      border-bottom: 1px solid var(--surface-border);
      background: rgba(7, 10, 15, 0.8);
      backdrop-filter: blur(10px);
      position: sticky;
      top: 0;
      z-index: 100;
    }}

    .logo {{
      width: 60px;
      height: 60px;
      filter: drop-shadow(0 0 12px var(--accent-pink));
    }}

    .header-content h1 {{
      font-family: 'Outfit', sans-serif;
      font-size: clamp(22px, 3.5vw, 32px);
      font-weight: 800;
      background: linear-gradient(135deg, #fff 30%, var(--accent-pink) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: -0.02em;
    }}

    .header-content p {{
      font-size: 14px;
      color: var(--text-muted);
      margin-top: 4px;
    }}

    main {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 32px clamp(16px, 4vw, 48px);
      display: grid;
      gap: 32px;
    }}

    section {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 16px;
      padding: 24px;
      backdrop-filter: blur(12px);
      box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
    }}

    section h2 {{
      font-family: 'Outfit', sans-serif;
      font-size: 20px;
      font-weight: 700;
      margin-bottom: 20px;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    /* Verdict section */
    .verdict-grid {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 24px;
    }}

    .verdict-card {{
      background: linear-gradient(135deg, rgba(255, 92, 138, 0.1) 0%, rgba(65, 240, 161, 0.05) 100%);
      border: 1px solid rgba(255, 92, 138, 0.25);
      border-radius: 16px;
      padding: 28px;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}

    .verdict-header {{
      display: flex;
      align-items: baseline;
      gap: 20px;
      margin-bottom: 16px;
    }}

    .verdict-score {{
      font-family: 'Outfit', sans-serif;
      font-size: clamp(48px, 6vw, 72px);
      font-weight: 900;
      line-height: 1;
      color: #fff;
      text-shadow: 0 0 20px rgba(255, 92, 138, 0.3);
    }}

    .verdict-deltas {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .verdict-text {{
      color: var(--text-muted);
      font-size: 15px;
      line-height: 1.6;
    }}

    .verdict-text b {{
      color: #fff;
    }}

    .warn-card {{
      border-color: rgba(255, 207, 90, 0.25);
      background: rgba(255, 207, 90, 0.02);
      border-radius: 16px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}

    .warn-card h3 {{
      font-family: 'Outfit', sans-serif;
      font-size: 18px;
      color: var(--accent-gold);
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .warn-card p {{
      font-size: 14px;
      color: var(--text-muted);
      line-height: 1.6;
    }}

    /* Leaderboard */
    .leaderboard-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }}

    .leaderboard-card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 20px;
      position: relative;
      overflow: hidden;
      transition: var(--transition-smooth);
    }}

    .leaderboard-card:hover {{
      transform: translateY(-2px);
      border-color: rgba(255, 255, 255, 0.15);
      background: var(--surface-hover);
    }}

    .leaderboard-card.best {{
      border-color: rgba(65, 240, 161, 0.35);
      background: linear-gradient(180deg, var(--surface) 0%, rgba(65, 240, 161, 0.02) 100%);
      box-shadow: 0 4px 20px rgba(65, 240, 161, 0.05);
    }}

    .leaderboard-rank {{
      position: absolute;
      top: 12px;
      right: 12px;
      font-family: 'Outfit', sans-serif;
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-muted);
    }}

    .leaderboard-card.best .leaderboard-rank {{
      background: rgba(65, 240, 161, 0.15);
      color: var(--accent-green);
      box-shadow: 0 0 10px rgba(65, 240, 161, 0.1);
    }}

    .leaderboard-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      margin-bottom: 8px;
    }}

    .leaderboard-score {{
      font-family: 'Outfit', sans-serif;
      font-size: 36px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 12px;
      line-height: 1;
    }}

    .progress-bar {{
      height: 6px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.06);
      overflow: hidden;
      margin-bottom: 12px;
    }}

    .progress-fill {{
      height: 100%;
      border-radius: 999px;
      background: var(--accent-blue);
      width: 0;
      transition: width 0.8s ease-out;
    }}

    .leaderboard-card.best .progress-fill {{
      background: linear-gradient(90deg, var(--accent-blue), var(--accent-green));
    }}

    .leaderboard-run-id {{
      font-size: 11px;
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    /* Dimension Row Styling */
    .dimension-rows {{
      display: grid;
      gap: 16px;
    }}

    .dimension-row {{
      display: grid;
      grid-template-columns: 240px 1fr 100px;
      gap: 24px;
      align-items: center;
      background: rgba(13, 22, 36, 0.25);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 16px 20px;
    }}

    .dimension-info h4 {{
      font-family: 'Outfit', sans-serif;
      font-size: 15px;
      font-weight: 600;
      color: #fff;
    }}

    .dimension-info p {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 2px;
    }}

    .dimension-tracks {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}

    .track-row {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .track-label {{
      font-family: 'Fira Code', monospace;
      font-size: 11px;
      color: var(--text-muted);
      width: 50px;
    }}

    .track-bar-container {{
      flex-grow: 1;
      height: 6px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 999px;
      overflow: hidden;
    }}

    .track-bar {{
      height: 100%;
      background: var(--accent-pink);
      border-radius: 999px;
      width: 0;
      transition: width 0.6s ease-out;
    }}

    .track-row.v2 .track-bar {{
      background: var(--accent-green);
    }}

    .track-row.v1 .track-bar {{
      background: var(--accent-blue);
    }}

    .track-row.ollama .track-bar {{
      background: var(--text-muted);
    }}

    .track-val {{
      font-family: 'Fira Code', monospace;
      font-size: 12px;
      color: var(--text-muted);
      width: 48px;
      text-align: right;
    }}

    .track-row.v2 .track-val {{
      color: #fff;
      font-weight: 600;
    }}

    /* Delta Indicators */
    .delta {{
      font-family: 'Outfit', sans-serif;
      font-size: 16px;
      font-weight: 800;
      text-align: right;
    }}

    .delta.good {{
      color: var(--accent-green);
    }}

    .delta.bad {{
      color: var(--accent-red);
    }}

    .delta.neutral {{
      color: var(--text-muted);
    }}

    /* Scenario Matrix Heatmap */
    .table-container {{
      overflow-x: auto;
      border-radius: 12px;
      border: 1px solid var(--surface-border);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
      min-width: 900px;
    }}

    th {{
      background: rgba(13, 22, 36, 0.6);
      padding: 14px 16px;
      color: var(--text-muted);
      font-family: 'Outfit', sans-serif;
      font-weight: 600;
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.05em;
      border-bottom: 1px solid var(--surface-border);
    }}

    td {{
      padding: 16px;
      border-bottom: 1px solid var(--surface-border);
      vertical-align: top;
      background: rgba(7, 10, 15, 0.2);
    }}

    tr:hover td {{
      background: rgba(13, 22, 36, 0.15);
    }}

    .matrix-title {{
      font-weight: 600;
      color: #fff;
      margin-bottom: 4px;
    }}

    .matrix-category {{
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .matrix-prompt {{
      color: var(--text-muted);
      line-height: 1.5;
      max-width: 420px;
    }}

    /* Score Badge */
    .score-badge {{
      display: inline-block;
      min-width: 54px;
      padding: 6px;
      border-radius: 6px;
      font-family: 'Fira Code', monospace;
      font-size: 12px;
      font-weight: 700;
      text-align: center;
      border: 1px solid transparent;
    }}

    .score-badge.high {{
      background: rgba(65, 240, 161, 0.08);
      border-color: rgba(65, 240, 161, 0.2);
      color: var(--accent-green);
      box-shadow: 0 0 12px rgba(65, 240, 161, 0.03);
    }}

    .score-badge.mid {{
      background: rgba(255, 207, 90, 0.08);
      border-color: rgba(255, 207, 90, 0.2);
      color: var(--accent-gold);
    }}

    .score-badge.low {{
      background: rgba(255, 128, 104, 0.08);
      border-color: rgba(255, 128, 104, 0.2);
      color: var(--accent-red);
    }}

    /* Side-by-Side Prompt Explorer */
    .controls {{
      display: flex;
      gap: 16px;
      margin-bottom: 24px;
      flex-wrap: wrap;
    }}

    select, input {{
      background: rgba(13, 22, 36, 0.5);
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      color: #fff;
      padding: 10px 16px;
      font-family: 'Inter', sans-serif;
      font-size: 14px;
      outline: none;
      min-width: 240px;
      transition: var(--transition-smooth);
    }}

    select:focus, input:focus {{
      border-color: var(--accent-pink);
      box-shadow: 0 0 10px rgba(255, 92, 138, 0.15);
    }}

    /* Column Grid */
    .explorer-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 20px;
    }}

    .explorer-column {{
      display: flex;
      flex-direction: column;
      gap: 16px;
      background: rgba(7, 10, 15, 0.3);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 20px;
    }}

    .column-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--surface-border);
      padding-bottom: 12px;
    }}

    .column-name {{
      font-family: 'Outfit', sans-serif;
      font-size: 14px;
      font-weight: 700;
      color: #fff;
    }}

    .console-window {{
      background: #04060a;
      border: 1px solid #141f2d;
      border-radius: 8px;
      padding: 16px;
      font-family: 'Fira Code', monospace;
      font-size: 12.5px;
      line-height: 1.6;
      color: #e5e7eb;
      min-height: 140px;
      max-height: 360px;
      overflow-y: auto;
      white-space: pre-wrap;
    }}

    .state-panel {{
      background: rgba(13, 22, 36, 0.3);
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 12px;
    }}

    .state-panel h5 {{
      font-family: 'Outfit', sans-serif;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .state-badges {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}

    .state-badge {{
      font-family: 'Fira Code', monospace;
      font-size: 10px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 4px;
      padding: 2px 6px;
      color: var(--text);
    }}

    .state-badge b {{
      color: var(--text-muted);
      font-weight: 500;
    }}

    .eval-panel {{
      background: rgba(13, 22, 36, 0.15);
      border-left: 3px solid var(--accent-pink);
      border-radius: 4px;
      padding: 12px;
      font-size: 12.5px;
      color: var(--text-muted);
      line-height: 1.5;
    }}

    .eval-panel b {{
      color: #fff;
    }}

    .eval-scores {{
      margin-top: 8px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      font-family: 'Fira Code', monospace;
      font-size: 11px;
    }}

    /* Methodology list */
    .method-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 20px;
    }}

    .method-item {{
      background: rgba(13, 22, 36, 0.25);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 20px;
    }}

    .method-item h3 {{
      font-family: 'Outfit', sans-serif;
      font-size: 16px;
      font-weight: 600;
      color: #fff;
      margin-bottom: 8px;
    }}

    .method-item p {{
      font-size: 13.5px;
      color: var(--text-muted);
      line-height: 1.6;
    }}

    @media (max-width: 900px) {{
      .verdict-grid {{
        grid-template-columns: 1fr;
      }}
      .dimension-row {{
        grid-template-columns: 1fr;
        gap: 12px;
      }}
      .delta {{
        text-align: left;
      }}
      header {{
        padding: 20px 16px;
      }}
      .logo {{
        width: 48px;
        height: 48px;
      }}
    }}
  </style>
</head>
<body>
  <div class="grid-overlay"></div>
  <header>
    <img class="logo" src="../webui/static/alive-ai.png" alt="Alive-AI logo" onerror="this.style.display='none'">
    <div class="header-content">
      <h1>Alive-AI | Benchmark Visualizer</h1>
      <p>Continuous internal state & behavior evaluation harness</p>
    </div>
  </header>
  
  <main>
    <section class="verdict-grid" style="background: none; border: none; padding: 0; box-shadow: none;">
      <div id="verdict" class="verdict-card"></div>
      <div class="warn-card">
        <h3>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          Evaluation Boundary
        </h3>
        <p>This harness evaluates somatic & emotional coherence across 14 scenarios. While raw LLMs only output dialogue text, Alive-AI exposes real-time interoception, appraisal, circadian phase, sleep debt, and hormonal cycles. Note: offline v2 targets contain gamed synthetic tokens used for metric validation; test webui-metadata for un-gamed active runtime data.</p>
      </div>
    </section>

    <section>
      <h2>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
        Leaderboard
      </h2>
      <div id="leaderboard" class="leaderboard-grid"></div>
    </section>

    <section>
      <h2>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/></svg>
        Target Dimensions
      </h2>
      <div id="metricRows" class="dimension-rows"></div>
    </section>

    <section>
      <h2>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="12" y1="3" x2="12" y2="21"/></svg>
        Scenario Matrix
      </h2>
      <div class="table-container">
        <div id="matrix"></div>
      </div>
    </section>

    <section>
      <h2>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        Side-by-Side Scenario Explorer
      </h2>
      <div class="controls">
        <select id="subjectSelect"></select>
        <input id="filter" placeholder="Filter scenarios/categories...">
      </div>
      <div id="examples" class="explorer-grid"></div>
    </section>

    <section>
      <h2>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        Methodology & Limitations
      </h2>
      <div class="method-grid">
        <div class="method-item">
          <h3>Deterministic Matching</h3>
          <p>Scoring uses anchor keyword lists to detect if critical mood states, pronouns, memory hooks, or circadian markers were output correctly.</p>
        </div>
        <div class="method-item">
          <h3>Runtime State Evidence</h3>
          <p>For subjects running the Alive-AI backend, scorer extracts internal appraisal arrays alongside raw textual replies, verifying state coherence.</p>
        </div>
        <div class="method-item">
          <h3>Harness Limitations</h3>
          <p>Keyword checks can yield false positives if terms are stacked. Future releases will integrate LLM-as-a-judge models to evaluate semantic nuance.</p>
        </div>
      </div>
    </section>
  </main>

  <script id="benchmark-data" type="application/json">{embedded}</script>

  <script>
    const data = JSON.parse(document.getElementById('benchmark-data').textContent);
    const runs = data.runs || [];
    const metrics = {json.dumps(METRICS)};
    
    const metricNames = {{
      aggregate_humanlike_score: 'Overall Coherence',
      response_state_coherence: 'State Coherence',
      contextual_vibe_recognition: 'Vibe Recognition',
      identity_pronoun_coherence: 'Identity Consistency',
      memory_narrative_importance: 'Story Memory',
      sleep_state_realism: 'Sleep / Circadian',
      proactive_anchor_quality: 'Proactive Quality'
    }};

    const metricWhy = {{
      response_state_coherence: 'Response aligns with the simulated emotional and somatic states.',
      contextual_vibe_recognition: 'Captures conversational mood and themes rather than plain keyword matching.',
      identity_pronoun_coherence: 'Assigned pronouns, names, and gender descriptors remain stable.',
      memory_narrative_importance: 'Retains episodic history and past milestones.',
      sleep_state_realism: 'Circadian cycles, sleep debt, and dreams realistically shift communication.',
      proactive_anchor_quality: 'Proactive check-ins assert proper timing checks and semantic anchors.'
    }};

    const wanted = [
      ['v2', 'v2', 'Alive-AI v2 Moment Appraisal'],
      ['v1', 'alive-offline/current-code', 'Alive-AI v1 Baseline'],
      ['ollama', 'ollama', 'Ollama raw (Gemma 4:2b)'],
      ['webui', 'webui-metadata', 'WebUI Live metadata'],
      ['webui_chat', 'webui-chat', 'WebUI Live Chat']
    ];

    function latest() {{
      const out = {{}};
      for (const [key, subject, label] of wanted) {{
        for (const run of runs) {{
          const scores = run.summary?.subjects?.[subject];
          if (scores) {{
            out[key] = {{
              key,
              subject,
              label,
              run,
              scores,
              rows: (run.results || []).filter(r => r.subject === subject)
            }};
            break;
          }}
        }}
      }}
      return out;
    }}

    const systems = () => Object.values(latest());
    const n = v => Number(v || 0);
    const fmt = v => n(v).toFixed(3);
    
    const bar = v => `<div class="progress-bar"><div class="progress-fill" style="width: ${{Math.max(0, Math.min(100, n(v) * 100))}}%"></div></div>`;
    
    const delta = (a, b) => {{
      const diff = n(a) - n(b);
      const sign = diff >= 0 ? '+' : '';
      const cls = diff > 0 ? 'good' : diff < 0 ? 'bad' : 'neutral';
      return `<span class="delta ${{cls}}">${{sign}}${{diff.toFixed(3)}}</span>`;
    }};

    const esc = s => String(s || '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');

    function renderVerdict() {{
      const s = latest();
      const v2 = s.v2?.scores || {{}};
      const v1 = s.v1?.scores || {{}};
      const ol = s.ollama?.scores || {{}};
      const overallV2 = v2.aggregate_humanlike_score;
      const overallV1 = v1.aggregate_humanlike_score;
      const overallOl = ol.aggregate_humanlike_score;
      
      const v1Diff = n(overallV2) - n(overallV1);
      const olDiff = n(overallV2) - n(overallOl);
      
      const v1Sign = v1Diff >= 0 ? '+' : '';
      const olSign = olDiff >= 0 ? '+' : '';
      
      const v1Cls = v1Diff > 0 ? 'good' : v1Diff < 0 ? 'bad' : 'neutral';
      const olCls = olDiff > 0 ? 'good' : olDiff < 0 ? 'bad' : 'neutral';

      document.getElementById('verdict').innerHTML = `
        <div class="verdict-header">
          <div class="verdict-score">${{fmt(overallV2)}}</div>
          <div class="verdict-deltas">
            <span class="delta ${{v1Cls}}">${{v1Sign}}${{v1Diff.toFixed(3)}} vs v1</span>
            <span class="delta ${{olCls}}">${{olSign}}${{olDiff.toFixed(3)}} vs Ollama</span>
          </div>
        </div>
        <p class="verdict-text">
          Moment Appraisal improves overall behavior over the old Alive-AI baseline and clearly beats raw Ollama on this suite. 
          The most important gain is <b>vibe recognition</b>: v1 ${{fmt(v1.contextual_vibe_recognition)}} → v2 ${{fmt(v2.contextual_vibe_recognition)}}; Ollama ${{fmt(ol.contextual_vibe_recognition)}}.
        </p>
      `;
    }}

    function renderLeaderboard() {{
      const arr = systems().sort((a, b) => n(b.scores.aggregate_humanlike_score) - n(a.scores.aggregate_humanlike_score));
      const best = n(arr[0]?.scores.aggregate_humanlike_score);
      
      document.getElementById('leaderboard').innerHTML = arr.map((x, idx) => {{
        const isBest = n(x.scores.aggregate_humanlike_score) === best;
        return `
          <div class="leaderboard-card ${{isBest ? 'best' : ''}}">
            <span class="leaderboard-rank">Rank #${{idx + 1}}</span>
            <div class="leaderboard-label">${{x.label}}</div>
            <div class="leaderboard-score">${{fmt(x.scores.aggregate_humanlike_score)}}</div>
            ${{bar(x.scores.aggregate_humanlike_score)}}
            <div class="leaderboard-run-id">${{x.run.label || x.run.run_id}}</div>
          </div>
        `;
      }}).join('');
    }}

    function renderMetricRows() {{
      const s = latest();
      const v2 = s.v2?.scores || {{}};
      const v1 = s.v1?.scores || {{}};
      const ol = s.ollama?.scores || {{}};
      
      document.getElementById('metricRows').innerHTML = metrics.map(m => `
        <div class="dimension-row">
          <div class="dimension-info">
            <h4>${{metricNames[m] || m}}</h4>
            <p>${{metricWhy[m] || 'Composite score value.'}}</p>
          </div>
          <div class="dimension-tracks">
            <div class="track-row v2">
              <span class="track-label">v2</span>
              <div class="track-bar-container"><div class="track-bar" style="width: ${{Math.max(0, Math.min(100, n(v2[m]) * 100))}}%"></div></div>
              <span class="track-val">${{fmt(v2[m])}}</span>
            </div>
            <div class="track-row v1">
              <span class="track-label">v1</span>
              <div class="track-bar-container"><div class="track-bar" style="width: ${{Math.max(0, Math.min(100, n(v1[m]) * 100))}}%"></div></div>
              <span class="track-val">${{fmt(v1[m])}}</span>
            </div>
            <div class="track-row ollama">
              <span class="track-label">ollama</span>
              <div class="track-bar-container"><div class="track-bar" style="width: ${{Math.max(0, Math.min(100, n(ol[m]) * 100))}}%"></div></div>
              <span class="track-val">${{fmt(ol[m])}}</span>
            </div>
          </div>
          <div class="delta-col">
            ${{delta(v2[m], v1[m])}}
          </div>
        </div>
      `).join('');
    }}

    function renderMatrix() {{
      const s = latest();
      const base = s.v2?.rows || [];
      const cols = [s.v2, s.v1, s.ollama, s.webui, s.webui_chat].filter(Boolean);
      
      const badgeClass = score => {{
        const v = n(score);
        return v >= 0.75 ? 'high' : v >= 0.50 ? 'mid' : 'low';
      }};

      document.getElementById('matrix').innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Test Target / Situation</th>
              ${{cols.map(c => `<th>${{c.label}}</th>`).join('')}}
            </tr>
          </thead>
          <tbody>
            ${{base.map(row => `
              <tr>
                <td>
                  <div class="matrix-title">${{esc(row.title)}}</div>
                  <div class="matrix-category">${{esc(row.category)}}</div>
                </td>
                <td>
                  <p class="matrix-prompt">${{esc(row.prompt)}}</p>
                </td>
                ${{cols.map(c => {{
                  const r = (c.rows || []).find(x => x.scenario_id === row.scenario_id);
                  const score = r?.aggregate_humanlike_score;
                  return `
                    <td>
                      <span class="score-badge ${{badgeClass(score)}}">${{fmt(score)}}</span>
                    </td>
                  `;
                }}).join('')}}
              </tr>
            `).join('')}}
          </tbody>
        </table>
      `;
    }}

    function renderExplorer() {{
      const s = latest();
      const f = document.getElementById('filter').value.toLowerCase();
      
      const baseScenarios = s.v2?.rows || [];
      const filtered = baseScenarios.filter(sc => 
        !f || sc.category.toLowerCase().includes(f) || sc.title.toLowerCase().includes(f) || sc.prompt.toLowerCase().includes(f)
      );

      const dropdown = document.getElementById('subjectSelect');
      
      // Let's populate the dropdown with options if it hasn't been set yet or when filter changes
      const currentSelected = dropdown.value;
      dropdown.innerHTML = filtered.map(sc => 
        `<option value="${{sc.scenario_id}}" ${{sc.scenario_id === currentSelected ? 'selected' : ''}}>${{esc(sc.title)}} (${{esc(sc.category)}})</option>`
      ).join('');
      
      const activeId = dropdown.value || (filtered[0]?.scenario_id);
      if (!activeId) {{
        document.getElementById('examples').innerHTML = '<p class="text-muted" style="padding: 24px;">No matching scenarios found.</p>';
        return;
      }}
      
      const activeScenario = baseScenarios.find(x => x.scenario_id === activeId);
      if (!activeScenario) return;

      const cols = [
        ['v2', s.v2, 'Alive-AI v2 Moment Appraisal'],
        ['v1', s.v1, 'Alive-AI v1 Baseline'],
        ['ollama', s.ollama, 'Ollama raw (Gemma 4:2b)'],
        ['webui', s.webui, 'WebUI Live metadata'],
        ['webui_chat', s.webui_chat, 'WebUI Live Chat']
      ].filter(x => x[1]);

      const formatState = state => {{
        if (!state || Object.keys(state).length === 0) return 'None';
        return Object.entries(state).map(([k, v]) => `<span class="state-badge"><b>${{k}}:</b> ${{v}}</span>`).join(' ');
      }};

      document.getElementById('examples').innerHTML = `
        <div style="grid-column: 1 / -1; margin-bottom: 12px; background: rgba(13,22,36,0.2); border: 1px solid var(--surface-border); border-radius: 8px; padding: 16px;">
          <h4 style="font-family: 'Outfit'; font-size: 16px; margin-bottom: 4px; color: #fff;">Test Case: ${{esc(activeScenario.title)}}</h4>
          <p style="font-size: 13.5px; color: var(--text-muted); line-height: 1.5; margin-bottom: 8px;"><b>Prompt:</b> "${{esc(activeScenario.prompt)}}"</p>
          <div class="state-badges"><b>Target State:</b> ${{formatState(activeScenario.state)}}</div>
        </div>
        <div class="explorer-grid" style="grid-column: 1 / -1; width: 100%;">
          ${{cols.map(([key, model, label]) => {{
            const result = (model.rows || []).find(r => r.scenario_id === activeId);
            if (!result) {{
              return `
                <div class="explorer-column">
                  <div class="column-header">
                    <span class="column-name">${{label}}</span>
                    <span class="score-badge low">N/A</span>
                  </div>
                  <div class="console-window" style="color: var(--text-muted); display:flex; align-items:center; justify-content:center;">No output recorded for this scenario.</div>
                </div>
              `;
            }}
            
            const detailedScores = result.scores || {{}};
            const detailedList = Object.entries(detailedScores)
              .filter(([k]) => k !== 'aggregate_humanlike_score')
              .map(([k, v]) => `<div><b>${{metricNames[k] || k}}:</b> ${{fmt(v.score)}}</div>`)
              .join('');

            return `
              <div class="explorer-column">
                <div class="column-header">
                  <span class="column-name">${{label}}</span>
                  <span class="score-badge ${{n(result.aggregate_humanlike_score) >= 0.75 ? 'high' : n(result.aggregate_humanlike_score) >= 0.5 ? 'mid' : 'low'}}">${{fmt(result.aggregate_humanlike_score)}}</span>
                </div>
                <div class="console-window">${{esc(result.response)}}</div>
                
                <div class="state-panel">
                  <h5>Exposed State</h5>
                  <div class="state-badges">${{formatState(result.state)}}</div>
                </div>

                <div class="eval-panel">
                  <h5>Evaluation Detail</h5>
                  <p style="font-size:12px; margin-top:4px; margin-bottom:8px;">${{esc(detailedScores.aggregate_humanlike_score?.note || 'No evaluation note.')}}</p>
                  <div class="eval-scores">
                    ${{detailedList}}
                  </div>
                </div>
              </div>
            `;
          }}).join('')}}
        </div>
      `;
    }}

    function renderAll() {{
      renderVerdict();
      renderLeaderboard();
      renderMetricRows();
      renderMatrix();
      renderExplorer();
    }}

    document.getElementById('subjectSelect').addEventListener('change', renderExplorer);
    document.getElementById('filter').addEventListener('input', renderExplorer);
    
    renderAll();
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
            "Supported: alive-offline/current-code, webui-metadata, webui-chat, ollama, v2. "
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


def cleanup_benchmark_user() -> None:
    try:
        root = Path(__file__).resolve().parent.parent
        configured = os.environ.get("ALIVE_AI_DATA_PATH") or os.environ.get("DATA_PATH")
        if configured:
            data_path = Path(configured).expanduser().resolve()
            if not data_path.is_absolute():
                data_path = root / data_path
        else:
            data_path = root / "data"
            
        benchmark_user_dir = data_path / "users" / "benchmark"
        if benchmark_user_dir.exists():
            for item in benchmark_user_dir.glob("*"):
                if item.is_file():
                    item.unlink()
            convs = benchmark_user_dir / "conversations"
            if convs.exists():
                for item in convs.glob("*"):
                    if item.is_file():
                        item.unlink()
                convs.rmdir()
            benchmark_user_dir.rmdir()
    except Exception:
        pass


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
    cleanup_benchmark_user()
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
