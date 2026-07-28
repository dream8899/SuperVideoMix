#!/usr/bin/env python3
"""Content-aware video splitting — detect scene change peaks without fixed cadence.

Usage:
  # Analyze + preview a directory
  python3 content_split.py --input-dir DIR --output-dir PREVIEW_DIR --analyze --preview

  # Execute splits from saved analyses
  python3 content_split.py --input-dir DIR --analysis-dir PREVIEW_DIR --execute --output-dir OUT_DIR
"""

from __future__ import annotations

import argparse, csv, json, re, subprocess, sys
from pathlib import Path
from statistics import median

DEFAULT_MIN_HEIGHT = 0.15
DEFAULT_MIN_DISTANCE = 1.5
DEFAULT_MIN_SEGMENT = 2.0
DEFAULT_MIN_CUT_FROM_START = 3.0


# ── ffmpeg helpers ──────────────────────────────────────────────

def run_ff(command: list[str]) -> str:
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "ffmpeg command failed")
    return proc.stdout


def probe(path: Path) -> dict:
    payload = json.loads(
        run_ff(["ffprobe", "-v", "error", "-show_entries",
                "stream=index,codec_type,width,height,r_frame_rate,duration:format=duration",
                "-of", "json", str(path)]))
    video = next(s for s in payload["streams"] if s["codec_type"] == "video")
    audio = next((s for s in payload["streams"] if s["codec_type"] == "audio"), None)
    dur = float(video.get("duration") or payload["format"]["duration"])
    return {"width": int(video["width"]), "height": int(video["height"]),
            "fps": video["r_frame_rate"], "video_duration": dur, "has_audio": audio is not None}


def scene_scores(path: Path) -> list[tuple[float, float]]:
    out = run_ff(["ffmpeg", "-v", "error", "-i", str(path),
                  "-vf", "select='gte(scene,0)',metadata=print:file=-",
                  "-an", "-f", "null", "-"])
    times = [float(t) for t in re.findall(r"pts_time:([0-9.]+)", out)]
    scores = [float(s) for s in re.findall(r"lavfi\.scene_score=([0-9.]+)", out)]
    return list(zip(times, scores))


def detect_black_tail(path: Path, video_duration: float) -> tuple[float, dict | None]:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "info", "-i", str(path),
         "-vf", "blackdetect=d=1.0:pix_th=0.10", "-an", "-f", "null", "-"],
        capture_output=True, text=True)
    matches = re.findall(r"black_start:([0-9.]+)\s+black_end:([0-9.]+)\s+black_duration:([0-9.]+)", proc.stderr)
    tails = [(float(s), float(e), float(d)) for s, e, d in matches
             if float(e) >= video_duration - 0.2 and float(d) >= 1.0]
    if not tails:
        return video_duration, None
    s, e, d = tails[-1]
    return s, {"start": s, "end": e, "duration": d}


# ── peak detection ──────────────────────────────────────────────

def find_peaks(scores: list[tuple[float, float]], min_height: float = DEFAULT_MIN_HEIGHT,
               min_distance: float = DEFAULT_MIN_DISTANCE) -> list[tuple[float, float, str]]:
    """Find scene change peaks from all frame scores. Returns [(time, score, confidence)]."""
    if not scores:
        return []

    candidates = [(t, s) for t, s in scores if s >= min_height and t > 0.1]
    if not candidates:
        return []

    # cluster nearby peaks
    clusters = [[candidates[0]]]
    for c in candidates[1:]:
        if c[0] - clusters[-1][-1][0] <= min_distance:
            clusters[-1].append(c)
        else:
            clusters.append([c])
    peaks = []
    for cl in clusters:
        t, s = max(cl, key=lambda x: x[1])
        conf = "high" if s >= 0.4 else "medium" if s >= 0.25 else "low"
        peaks.append((t, s, conf))
    return peaks


# ── analysis ────────────────────────────────────────────────────

def analyze_content(path: Path, min_height: float = DEFAULT_MIN_HEIGHT,
                    min_distance: float = DEFAULT_MIN_DISTANCE,
                    min_segment: float = DEFAULT_MIN_SEGMENT,
                    min_cut_from_start: float = DEFAULT_MIN_CUT_FROM_START) -> dict:
    media = probe(path)
    usable_dur, black_tail = detect_black_tail(path, media["video_duration"])
    scores = scene_scores(path)
    raw_peaks = find_peaks(scores, min_height=min_height, min_distance=min_distance)

    # filter: exclude near start and in black tail
    effective_end = usable_dur
    peaks = [(t, s, c) for t, s, c in raw_peaks
             if t >= min_cut_from_start and t <= effective_end - min_segment]

    # merge segments that would be too short
    if peaks:
        filtered = [peaks[0]]
        for p in peaks[1:]:
            if p[0] - filtered[-1][0] < min_segment:
                if p[1] > filtered[-1][1]:
                    filtered[-1] = p
            else:
                filtered.append(p)
        peaks = filtered

    points = [0.0] + [p[0] for p in peaks] + [effective_end]
    segments = []
    for i in range(len(points) - 1):
        segments.append({"index": i + 1, "start": round(points[i], 6),
                         "end": round(points[i + 1], 6),
                         "duration": round(points[i + 1] - points[i], 6)})

    # cadence candidates for comparison
    cadence_results = []
    for cadence in (10.0, 15.0):
        count = max(2, round(usable_dur / cadence))
        step = usable_dur / count
        expected = [step * idx for idx in range(1, count)]
        strengths = []
        for target in expected:
            nearby = [s for t, s in scores if abs(t - target) <= 2.5]
            strengths.append(max(nearby, default=0.0))
        cadence_results.append({"cadence": cadence, "count": count, "step": step,
                                "expected": expected, "strengths": strengths,
                                "score": round(median(strengths) + sum(strengths) / max(1, len(strengths)), 6)})

    low_conf = [p for p in peaks if p[2] == "low"]
    needs_review = len(low_conf) > 0 or len(peaks) == 0

    return {"input": str(path), "media": media, "usable_duration": usable_dur,
            "ignored_black_tail": black_tail, "method": "content_peak_detection",
            "cadence_candidates": cadence_results,
            "detected_peaks": [{"time": round(p[0], 6), "score": round(p[1], 4), "confidence": p[2]} for p in peaks],
            "parameters": {"min_height": min_height, "min_distance": min_distance,
                           "min_segment": min_segment, "min_cut_from_start": min_cut_from_start},
            "segments": segments, "status": "needs_review" if needs_review else "ready"}


# ── preview ─────────────────────────────────────────────────────

def make_preview(path: Path, analysis: dict, preview_dir: Path):
    """Extract frames at segment midpoints and near cut points."""
    preview_dir.mkdir(parents=True, exist_ok=True)
    segments = analysis["segments"]
    peaks = analysis.get("detected_peaks", [])

    # midpoints
    for seg in segments:
        t = (seg["start"] + seg["end"]) / 2
        dest = preview_dir / f"seg{seg['index']:02d}_mid_{t:.1f}s.jpg"
        if dest.exists():
            continue
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path),
                        "-frames:v", "1", "-q:v", "3", str(dest)], check=False)

    # near cuts
    for p in peaks:
        for offset, label in [(-0.3, "before"), (0.0, "at"), (0.3, "after")]:
            ts = max(0.1, p["time"] + offset)
            dest = preview_dir / f"cut_{p['time']:.1f}s_{label}.jpg"
            if dest.exists():
                continue
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{ts:.3f}", "-i", str(path),
                            "-frames:v", "1", "-q:v", "3", str(dest)], check=False)


# ── split execution ─────────────────────────────────────────────

def split_one(path: Path, analysis: dict, output_root: Path) -> dict:
    segments = analysis["segments"]
    media = analysis["media"]
    parameters = analysis.get("parameters", {})
    min_cut_from_start = float(parameters.get("min_cut_from_start", DEFAULT_MIN_CUT_FROM_START))
    min_segment = float(parameters.get("min_segment", DEFAULT_MIN_SEGMENT))

    # filter: keep only cuts >= min_cut_from_start
    valid_starts = set()
    for i in range(1, len(segments)):
        if segments[i]["start"] >= min_cut_from_start:
            valid_starts.add(segments[i]["start"])

    if not valid_starts:
        return {"file": path.name, "status": "skipped", "reason": "all_cuts_too_early"}

    points = [0.0] + sorted(valid_starts) + [analysis["usable_duration"]]
    final_segs = []
    for i in range(len(points) - 1):
        dur = points[i + 1] - points[i]
        if dur >= min_segment:
            final_segs.append({"index": i + 1, "start": points[i], "end": points[i + 1], "duration": dur})

    if len(final_segs) <= 1:
        return {"file": path.name, "status": "skipped", "reason": "single_after_filter"}

    out_dir = output_root / path.stem
    if out_dir.exists():
        return {"file": path.name, "status": "skipped", "reason": "output_exists"}
    out_dir.mkdir(parents=True)

    n = len(final_segs)
    has_audio = media["has_audio"]
    vs = "".join(f"[vsrc{i+1}]" for i in range(n))
    filters = [f"[0:v]split={n}{vs}"]
    if has_audio:
        a_s = "".join(f"[asrc{i+1}]" for i in range(n))
        filters.append(f"[0:a]asplit={n}{a_s}")
    for seg in final_segs:
        idx = seg["index"]
        filters.append(f"[vsrc{idx}]trim=start={seg['start']:.6f}:end={seg['end']:.6f},setpts=PTS-STARTPTS[v{idx}]")
        if has_audio:
            filters.append(f"[asrc{idx}]atrim=start={seg['start']:.6f}:end={seg['end']:.6f},asetpts=PTS-STARTPTS[a{idx}]")

    cmd = ["ffmpeg", "-hide_banner", "-v", "error", "-n", "-i", str(path),
           "-filter_complex", ";".join(filters)]
    for seg in final_segs:
        idx = seg["index"]
        dest = out_dir / f"{idx:02d}_t{seg['start']:.1f}-{seg['end']:.1f}s.mp4"
        seg["file"] = str(dest)
        cmd.extend(["-map", f"[v{idx}]"])
        if has_audio:
            cmd.extend(["-map", f"[a{idx}]"])
        cmd.extend(["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p"])
        if has_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        cmd.extend(["-movflags", "+faststart", str(dest)])

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
    except subprocess.CalledProcessError as e:
        return {"file": path.name, "status": "failed", "reason": f"ffmpeg: {e.stderr[-200:] if e.stderr else e}"}

    # verify
    verified = True
    for seg in final_segs:
        dest = Path(seg["file"])
        if not dest.is_file():
            verified = False
            continue
        try:
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(dest), "-f", "null", "-"],
                           capture_output=True, text=True, timeout=30, check=True)
        except:
            verified = False

    # manifest
    manifest = out_dir / "拆分清单.tsv"
    with manifest.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["index", "start", "end", "duration", "file", "verified"], delimiter="\t")
        w.writeheader()
        for seg in final_segs:
            w.writerow({"index": seg["index"], "start": f"{seg['start']:.3f}",
                        "end": f"{seg['end']:.3f}", "duration": f"{seg['duration']:.3f}",
                        "file": Path(seg["file"]).name, "verified": True})

    return {"file": path.name, "status": "ok", "segments": len(final_segs),
            "output_dir": str(out_dir), "verified": verified}


# ── CLI ─────────────────────────────────────────────────────────

def cmd_analyze(args):
    all_mp4s = sorted(Path(args.input_dir).glob("*.mp4"))
    mp4s = [f for f in all_mp4s if "__h264-aac" not in f.name] or all_mp4s
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summaries = []
    for i, f in enumerate(mp4s):
        ana_path = out_dir / f"{f.stem}_content_analysis.json"
        if ana_path.exists():
            summaries.append(json.loads(ana_path.read_text()))
        else:
            print(f"\r分析: [{i+1}/{len(mp4s)}] {f.stem[:45]}...", end="", flush=True)
            try:
                r = analyze_content(f, min_height=args.min_height, min_distance=args.min_distance,
                                    min_segment=args.min_segment, min_cut_from_start=args.min_cut_from_start)
                ana_path.write_text(json.dumps(r, ensure_ascii=False, indent=2))
                summaries.append(r)
            except Exception as e:
                print(f"\n  ❌ {f.name}: {e}")

        if args.preview:
            try:
                prev_dir = out_dir / f"{f.stem}_content_frames"
                make_preview(f, summaries[-1], prev_dir)
            except:
                pass

    print()

    # summary
    total_segs = sum(len(r["segments"]) for r in summaries)
    single = sum(1 for r in summaries if len(r["segments"]) <= 1)
    print(f"\n=== 内容感知分析 ===")
    print(f"视频: {len(summaries)}  总段数: {total_segs}  单段: {single}")

    tsv_path = out_dir / "_content_summary.tsv"
    with tsv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["file", "duration", "segments", "cut_times", "status"])
        for r in summaries:
            cuts = ",".join(f"{p['time']:.1f}s" for p in r.get("detected_peaks", []))
            w.writerow([Path(r["input"]).name, f"{r['media']['video_duration']:.1f}s",
                        len(r["segments"]), cuts, r["status"]])
    print(f"TSV: {tsv_path}")


def cmd_execute(args):
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_mp4s = sorted(Path(args.input_dir).glob("*.mp4"))
    mp4s = [f for f in all_mp4s if "__h264-aac" not in f.name] or all_mp4s
    analysis_dir = Path(args.analysis_dir) if args.analysis_dir else None

    ok, skipped, failed = 0, 0, 0
    for i, f in enumerate(mp4s):
        ana_path = (analysis_dir / f"{f.stem}_content_analysis.json") if analysis_dir else None
        if not ana_path or not ana_path.is_file():
            print(f"\r拆分: [{i+1}/{len(mp4s)}] {f.stem[:45]}... 跳过(无分析文件)", end="", flush=True)
            skipped += 1
            continue

        print(f"\r拆分: [{i+1}/{len(mp4s)}] {f.stem[:45]}...", end="", flush=True)
        try:
            analysis = json.loads(ana_path.read_text())
            if len(analysis["segments"]) <= 1:
                skipped += 1
                continue
            result = split_one(f, analysis, out_dir)
            if result["status"] == "ok":
                ok += 1
            elif result["status"] == "skipped":
                skipped += 1
            else:
                failed += 1
                print(f"\n  ❌ {f.name}: {result.get('reason', '')}")
        except Exception as e:
            failed += 1
            print(f"\n  ❌ {f.name}: {e}")

    print(f"\n=== 完成 === 成功:{ok} 跳过:{skipped} 失败:{failed}")


def main():
    p = argparse.ArgumentParser(description="Content-aware video splitting via scene peak detection")
    p.add_argument("--input-dir", required=True, help="Directory containing MP4 files")
    p.add_argument("--output-dir", help="Output directory for previews or splits")
    p.add_argument("--analysis-dir", help="Directory containing saved _content_analysis.json files (for --execute)")
    p.add_argument("--analyze", action="store_true")
    p.add_argument("--preview", action="store_true", help="Generate preview frames at cut points")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--min-height", type=float, default=DEFAULT_MIN_HEIGHT)
    p.add_argument("--min-distance", type=float, default=DEFAULT_MIN_DISTANCE)
    p.add_argument("--min-segment", type=float, default=DEFAULT_MIN_SEGMENT)
    p.add_argument("--min-cut-from-start", type=float, default=DEFAULT_MIN_CUT_FROM_START)

    args = p.parse_args()

    if not args.output_dir:
        p.error("--output-dir is required")

    if args.analyze:
        cmd_analyze(args)
    if args.execute:
        cmd_execute(args)

    if not args.analyze and not args.execute:
        p.error("需要 --analyze 或 --execute")


if __name__ == "__main__":
    raise SystemExit(main())
