#!/usr/bin/env python3
"""
JP Movie/Audio -> Thai SRT translator
GPU-accelerated with faster-whisper + Ollama (local).

Usage:
  python translate.py movie.mp4
  python translate.py movie.mp4 --whisper large-v3 --ollama qwen2.5:7b
  python translate.py movie.mp4 --no-translate           # only transcribe to JP SRT
  python translate.py movie.mp4 --device cpu             # fallback: CPU only
"""
from __future__ import annotations
import argparse
import json
import signal
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Force UTF-8 stdout/stderr so emoji and Thai/Japanese chars work on Windows (cp1252 default)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass


# ---------- helpers ----------------------------------------------------------
def fmt_ts(t: float) -> str:
    """Seconds -> SRT timestamp HH:MM:SS,mmm"""
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        ms = 0
        s += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_secs(s: float) -> str:
    if s < 60:
        return f"{s:.1f}s"
    m = int(s // 60)
    return f"{m}m {int(s % 60)}s"


# ---------- Ollama -----------------------------------------------------------
PROMPT_TPL = (
    "แปลประโยคต่อไปนี้จากภาษาญี่ปุ่นเป็นภาษาไทย "
    "ตอบเฉพาะคำแปลเท่านั้น ไม่ต้องอธิบายหรือเพิ่มเติม:\n{text}"
)


def ollama_check(host: str, model: str) -> list[str]:
    """Return list of available models. Raises on connection error."""
    with urllib.request.urlopen(f"{host}/api/tags", timeout=5) as r:
        data = json.loads(r.read().decode("utf-8"))
    return [m["name"] for m in data.get("models", [])]


def ollama_translate(text: str, model: str, host: str, timeout: int = 120) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": PROMPT_TPL.format(text=text),
            "stream": False,
            # keep_alive="30m" tells Ollama to keep the model in VRAM between requests.
            # Without this, some Ollama setups unload the model after each call,
            # adding 5-10s of reload overhead per segment.
            "keep_alive": "30m",
            "options": {"temperature": 0.1, "num_predict": 200},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return (result.get("response") or "").strip()


# ---------- main -------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="JP -> TH subtitle translator (faster-whisper + Ollama, GPU)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python translate.py movie.mp4 --whisper large-v3 --ollama qwen2.5:7b",
    )
    ap.add_argument("input", help="Video or audio file (.mp4, .mkv, .mp3, .wav, ...)")
    ap.add_argument(
        "--whisper",
        default="large-v3",
        help="Whisper model: tiny / base / small / medium / large-v3 (default: large-v3)",
    )
    ap.add_argument(
        "--ollama",
        default="qwen2.5:7b",
        help="Ollama model for translation (default: qwen2.5:7b)",
    )
    ap.add_argument(
        "--ollama-host", default="http://localhost:11434", help="Ollama API base URL"
    )
    ap.add_argument(
        "--device",
        default="cuda",
        choices=["cuda", "cpu", "auto"],
        help="cuda (GPU, default) / cpu / auto",
    )
    ap.add_argument(
        "--compute-type",
        default="float16",
        help="float16 (GPU default) / int8_float16 (less VRAM) / int8 (CPU)",
    )
    ap.add_argument(
        "--no-translate",
        action="store_true",
        help="Only transcribe to JP SRT, skip Ollama translation",
    )
    ap.add_argument(
        "--output", "-o", help="Output SRT path (default: <input>_th.srt or _ja.srt)"
    )
    ap.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Whisper beam size (1 = greedy/fast, 5 = default/accurate)",
    )
    args = ap.parse_args()

    # ── Validate input ───────────────────────────────────────────────────
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"❌ File not found: {input_path}", file=sys.stderr)
        return 1

    suffix = "_ja.srt" if args.no_translate else "_th.srt"
    out_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else input_path.with_name(input_path.stem + suffix)
    )

    print(f"📁 Input : {input_path.name}  ({input_path.stat().st_size / 1048576:.1f} MB)")
    print(f"📁 Output: {out_path.name}")
    print(f"⚙️  Whisper={args.whisper}  Device={args.device}  Compute={args.compute_type}")
    if not args.no_translate:
        print(f"⚙️  Ollama={args.ollama}  Host={args.ollama_host}")
    print()

    # ── Check Ollama (only if translating) ───────────────────────────────
    if not args.no_translate:
        try:
            models = ollama_check(args.ollama_host, args.ollama)
        except urllib.error.URLError as e:
            print(
                f"❌ Cannot connect to Ollama at {args.ollama_host}\n"
                f"   Start it with: ollama serve\n"
                f"   Detail: {e}",
                file=sys.stderr,
            )
            return 2
        # Match exact or by prefix (qwen2.5:7b matches "qwen2.5:7b", "qwen2.5:7b-instruct" etc.)
        if not any(m == args.ollama or m.startswith(args.ollama + "-") for m in models):
            print(
                f"⚠️  Ollama model '{args.ollama}' not found.\n"
                f"   Available: {', '.join(models) or '(none)'}\n"
                f"   Pull it with: ollama pull {args.ollama}",
                file=sys.stderr,
            )
            return 3
        print(f"✓ Ollama OK — {len(models)} models available\n")

    # ── Lazy imports ─────────────────────────────────────────────────────
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        print(
            "❌ faster-whisper not installed.\n"
            "   pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 4
    try:
        from tqdm import tqdm  # type: ignore
    except ImportError:
        print("❌ tqdm not installed.\n   pip install tqdm", file=sys.stderr)
        return 4

    # ── Load model ───────────────────────────────────────────────────────
    print(f"📥 Loading Whisper '{args.whisper}'...")
    print("   (first run downloads model — large-v3 is ~3GB, cached after)")
    t0 = time.time()
    try:
        model = WhisperModel(
            args.whisper,
            device=args.device,
            compute_type=args.compute_type,
        )
    except Exception as e:
        msg = str(e)
        if "CUDA" in msg or "cuDNN" in msg or "cublas" in msg.lower():
            print(
                f"\n❌ GPU error: {e}\n\n"
                f"   ลองวิธีนี้:\n"
                f"   1. ติดตั้ง CUDA libs: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12\n"
                f"   2. หรือใช้ CPU: เพิ่ม --device cpu --compute-type int8",
                file=sys.stderr,
            )
        else:
            print(f"❌ {e}", file=sys.stderr)
        return 5
    print(f"   ✓ loaded in {fmt_secs(time.time() - t0)}\n")

    # ── Transcribe ───────────────────────────────────────────────────────
    print(f"🎵 Transcribing (JP)...")
    t0 = time.time()
    segments_iter, info = model.transcribe(
        str(input_path),
        language="ja",
        task="transcribe",
        beam_size=args.beam_size,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    duration = float(info.duration or 0)
    print(
        f"   detected lang: {info.language} ({info.language_probability:.0%})  "
        f"duration: {fmt_secs(duration)}"
    )

    segments: list[tuple[float, float, str]] = []
    with tqdm(
        total=max(int(duration), 1),
        unit="s",
        desc="  Whisper",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{rate_fmt}{postfix}]",
    ) as pbar:
        for seg in segments_iter:
            text = seg.text.strip()
            if text:
                segments.append((seg.start, seg.end, text))
            pbar.n = min(int(seg.end), pbar.total)
            pbar.set_postfix_str(f"{len(segments)} segs")
            pbar.refresh()
        pbar.n = pbar.total
        pbar.refresh()
    trans_time = time.time() - t0
    rtf = trans_time / duration if duration > 0 else 0
    print(f"   ✓ {len(segments)} segments in {fmt_secs(trans_time)}  (RTF {rtf:.2f}x)\n")

    if not segments:
        print("⚠️  No speech detected. Try smaller --whisper model or different file.")
        return 6

    # ── Translate (or skip) ──────────────────────────────────────────────
    if args.no_translate:
        translated = [(s, e, jp, jp) for s, e, jp in segments]
    else:
        print(f"🌏 Translating with Ollama ({args.ollama})...")
        t0 = time.time()
        translated = []
        failed = 0
        for start, end, jp in tqdm(
            segments,
            desc="  Ollama",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{rate_fmt}{postfix}]",
        ):
            try:
                th = ollama_translate(jp, args.ollama, args.ollama_host)
                if not th:
                    th = jp
                    failed += 1
            except Exception as e:
                failed += 1
                th = jp  # fallback to JP if translation fails
                tqdm.write(f"  ⚠️  [{fmt_ts(start)}] {type(e).__name__}: {e}")
            translated.append((start, end, jp, th))
        tr_time = time.time() - t0
        print(
            f"   ✓ {len(translated)} translated in {fmt_secs(tr_time)}  "
            f"({tr_time / max(len(translated), 1):.1f}s/seg, {failed} fallback)\n"
        )

    # ── Write SRT ────────────────────────────────────────────────────────
    parts: list[str] = []
    for i, (start, end, jp, th) in enumerate(translated, 1):
        text = jp if args.no_translate else th
        parts.append(f"{i}\n{fmt_ts(start)} --> {fmt_ts(end)}\n{text}\n")
    out_path.write_text("\n".join(parts), encoding="utf-8")

    print(f"✅ Saved: {out_path}")
    print(f"   {len(translated)} subtitles · {fmt_secs(duration)} audio")
    return 0


if __name__ == "__main__":
    # Graceful Ctrl+C
    signal.signal(signal.SIGINT, lambda *a: (print("\n⛔ Interrupted"), sys.exit(130)))
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⛔ Interrupted")
        sys.exit(130)
