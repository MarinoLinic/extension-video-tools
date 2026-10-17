from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fnmatch
import html
import json
import re
import xml.etree.ElementTree as ET


@dataclass
class Segment:
    start: float
    duration: float
    text: str


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text))).strip()


def seconds(value: str | float | None) -> float:
    if value is None:
        return 0.0
    value = str(value).replace(",", ".")
    if value.endswith("ms"):
        return float(value[:-2]) / 1000
    if value.endswith("s"):
        return float(value[:-1])
    parts = value.split(":")
    return sum(float(x) * 60 ** i for i, x in enumerate(reversed(parts)))


def parse_captions(raw: str | dict | list, fmt: str = "") -> list[Segment]:
    if isinstance(raw, str) and (fmt == "json3" or raw.lstrip().startswith(("{", "["))):
        raw = json.loads(raw)
    segments = []
    if isinstance(raw, dict):
        for event in raw.get("events", []):
            text = clean("".join(str(x.get("utf8", x.get("text", ""))) for x in event.get("segs", [])))
            if text:
                segments.append(Segment(float(event.get("tStartMs", 0)) / 1000, float(event.get("dDurationMs", 0)) / 1000, text))
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and clean(str(item.get("text", ""))):
                segments.append(Segment(float(item.get("start", 0)), float(item.get("duration", 0)), clean(str(item["text"]))))
    elif isinstance(raw, str) and raw.lstrip().startswith("<"):
        root = ET.fromstring(raw)
        for node in root.iter():
            tag = node.tag.rsplit("}", 1)[-1]
            if tag not in {"text", "p"}:
                continue
            text = clean("".join(node.itertext()))
            start = seconds(node.get("start", node.get("begin", node.get("t"))))
            duration = seconds(node.get("dur", node.get("d")))
            if node.get("t") is not None:
                start /= 1000
                duration /= 1000
            if node.get("end"):
                duration = max(0, seconds(node.get("end")) - start)
            if text:
                segments.append(Segment(start, duration, text))
    elif isinstance(raw, str):
        # VTT and SRT cue identifiers and styling blocks do not become speech.
        for block in re.split(r"\n\s*\n", raw.replace("\r", "").lstrip("\ufeff")):
            lines = block.splitlines()
            if not lines or lines[0].startswith(("NOTE", "STYLE", "REGION")):
                continue
            index = next((i for i, x in enumerate(lines) if "-->" in x), None)
            if index is None:
                continue
            match = re.search(r"([\d:. ,]+)\s+-->\s+([\d:.,]+)", lines[index])
            if not match:
                continue
            start, end = seconds(match[1].strip()), seconds(match[2])
            text = clean(" ".join(lines[index + 1:]))
            if text:
                segments.append(Segment(start, max(0, end - start), text))
    return normalize_segments(segments)


def normalize_segments(segments: list[Segment]) -> list[Segment]:
    result: list[Segment] = []
    previous: Segment | None = None
    for segment in sorted(segments, key=lambda x: x.start):
        text = clean(segment.text)
        original = Segment(segment.start, segment.duration, text)
        # Rolling VTT captions repeat the previous cue. Strip overlap only while
        # the original cue windows overlap; preserve repetition at separate times.
        if previous and segment.start < previous.start + previous.duration:
            old, new = previous.text.split(), text.split()
            for count in range(min(len(old), len(new)), 0, -1):
                if old[-count:] == new[:count]:
                    text = " ".join(new[count:])
                    break
        if text:
            result.append(Segment(segment.start, segment.duration, text))
        previous = original
    return result


def matches(language: str, requested: str) -> bool:
    requested = requested.replace(".*", "*")
    return fnmatch.fnmatchcase(language.lower(), requested.lower()) or language.lower().startswith(requested.lower() + "-")


def caption_candidates(info: dict, languages: tuple[str, ...], source: str, allow_translated: bool = False) -> list[tuple[str, str, dict]]:
    result = []
    sources = [("manual", info.get("subtitles") or {}), ("auto-generated", info.get("automatic_captions") or {})]
    if source == "manual":
        sources = sources[:1]
    elif source == "auto":
        sources = sources[1:]
    seen = set()
    for requested in languages:
        for kind, tracks in sources:
            for language in sorted(tracks, key=lambda x: (x != requested, x.endswith("-orig") is False, x)):
                if not matches(language, requested) or (not allow_translated and language.split("-")[0] == "live_chat"):
                    continue
                formats = sorted(tracks[language], key=lambda f: {"json3": 0, "srv3": 1, "ttml": 2, "vtt": 3, "srv1": 4, "srt": 5}.get(f.get("ext"), 99))
                for fmt in formats:
                    if fmt.get("ext") not in {"json3", "srv3", "ttml", "vtt", "srv1", "srt"} or not fmt.get("url"):
                        continue
                    # yt-dlp exposes translated caption URLs using tlang.
                    from urllib.parse import parse_qs, urlsplit
                    translated = "tlang" in parse_qs(urlsplit(fmt["url"]).query)
                    if not allow_translated and translated:
                        continue
                    key = fmt["url"]
                    if key not in seen:
                        seen.add(key)
                        result.append((language, kind + "-translated" if translated else kind, fmt))
    return result


def clock_text(value: float | int | None) -> str:
    if value is None:
        return "unknown"
    value = max(0, int(value))
    hours, rest = divmod(value, 3600)
    minutes, seconds_ = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{seconds_:02d}" if hours else f"{minutes}:{seconds_:02d}"


def markdown(meta: dict, segments: list[Segment], timestamps: bool = False, paragraphs: str = "readable") -> str:
    # JSON scalar quoting is valid YAML and keeps quotes/newlines/Unicode safe.
    header = "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in meta.items())
    title = re.sub(r"\s+", " ", str(meta["title"]))
    body = []
    if timestamps:
        for segment in segments:
            body.append(f"[{clock_text(segment.start)}]({meta['url']}&t={int(segment.start)}) {segment.text}")
    elif paragraphs == "single":
        body.append(" ".join(segment.text for segment in segments))
    else:
        paragraph: list[str] = []
        previous_end = 0.0
        for segment in segments:
            # Caption cues aren't paragraphs. Wait for sentence punctuation
            # before introducing a readability break, even for long passages.
            if paragraph and re.search(r'[.!?][\"\u201d\u2019\')]*$', paragraph[-1]) and (sum(len(x) + 1 for x in paragraph) >= 800 or segment.start - previous_end > 15):
                body.append(" ".join(paragraph))
                paragraph = []
            paragraph.append(segment.text)
            previous_end = segment.start + segment.duration
        if paragraph:
            body.append(" ".join(paragraph))
    return f"---\n{header}\n---\n\n# {title}\n\n" + "\n\n".join(body) + "\n"
