"""
pdf_to_audiobook.py

Converts a PDF to an audiobook using Kokoro or Parler TTS.
Configuration is read from pyproject.toml under [tool.pdf-to-audiobook]
"""

import argparse
import tomllib
import os
import sys
from pathlib import Path
import numpy as np
from tqdm import tqdm
import soundfile as sf
from pydub import AudioSegment
import nltk
from nltk.tokenize import sent_tokenize
from pypdf import PdfReader
import torch

# Download NLTK data once
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)


def load_config(config_path="pyproject.toml"):
    """Load settings from pyproject.toml [tool.pdf-to-audiobook] section."""
    if not os.path.isfile(config_path):
        print(f"Config file not found: {config_path}", file=sys.stderr)
        return {}

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLError as e:
        raise ValueError(f"Invalid TOML in {config_path}: {e}") from e

    config = data.get("tool", {}).get("pdf-to-audiobook", {})
    if not config:
        print(f"No [tool.pdf-to-audiobook] section found in {config_path}", file=sys.stderr)

    return config


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text += page_text + "\n\n"
    return text.strip()


def clean_text(text: str) -> str:
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines if line.strip() and not line.strip().isdigit()]
    return " ".join(cleaned).replace("  ", " ")


def split_text_into_chunks(text: str, max_words: int = 350) -> list[str]:
    sentences = sent_tokenize(text)
    chunks = []
    current = []
    current_count = 0

    for sentence in sentences:
        words = len(sentence.split())
        if current_count + words > max_words and current:
            chunks.append(" ".join(current))
            current = []
            current_count = 0
        current.append(sentence)
        current_count += words

    if current:
        chunks.append(" ".join(current))
    return chunks


def numpy_to_audio_segment(audio_array: np.ndarray, sample_rate: int) -> AudioSegment:
    if audio_array.ndim > 1:
        audio_array = np.mean(audio_array, axis=1)
    audio_array = np.clip(audio_array, -1.0, 1.0).astype(np.float32)
    int_array = (audio_array * 32767).astype(np.int16)
    return AudioSegment(
        data=int_array.tobytes(),
        sample_width=2,
        frame_rate=sample_rate,
        channels=1
    )


def load_tts(cfg: dict):
    tts_section = cfg.get("tts", {})
    engine = tts_section.get("engine", "kokoro").lower()

    if engine == "kokoro":
        from kokoro import KPipeline
        lang_code = tts_section.get("language_code", "a")
        pipeline = KPipeline(lang_code=lang_code)
        voice = tts_section.get("voice", "af_heart")
        print(f"Loaded Kokoro TTS with voice: {voice}")
        return {"engine": "kokoro", "pipeline": pipeline, "voice": voice, "sr": 24000}

    elif engine == "parler":
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer
        model_id = tts_section.get("parler_model", "parler-tts/parler-tts-mini-v1")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading Parler-TTS on {device}...")
        model = ParlerTTSForConditionalGeneration.from_pretrained(model_id).to(device)
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        description = tts_section.get(
            "parler_description",
            "A clear, professional narrator speaking calmly in American English."
        )
        return {
            "engine": "parler",
            "model": model,
            "tokenizer": tokenizer,
            "device": device,
            "description": description,
            "sr": model.config.sampling_rate
        }

    else:
        raise ValueError(f"Unsupported TTS engine: {engine}")


def generate_audio_chunk(tts: dict, text_chunk: str):
    if tts["engine"] == "kokoro":
        audio_pieces = []
        for _, _, audio in tts["pipeline"](text_chunk, voice=tts["voice"]):
            if len(audio) > 0:
                audio_pieces.append(audio)
        if audio_pieces:
            return np.concatenate(audio_pieces), tts["sr"]
        return np.array([]), tts["sr"]

    elif tts["engine"] == "parler":
        input_ids = tts["tokenizer"](tts["description"], return_tensors="pt").input_ids.to(tts["device"])
        prompt_input_ids = tts["tokenizer"](text_chunk, return_tensors="pt").input_ids.to(tts["device"])
        with torch.no_grad():
            generation = tts["model"].generate(
                input_ids=input_ids,
                prompt_input_ids=prompt_input_ids,
                do_sample=False,
                max_new_tokens=1024
            )
        audio_arr = generation.cpu().numpy().squeeze()
        return audio_arr, tts["sr"]


def main():
    parser = argparse.ArgumentParser(description="PDF → Audiobook using pyproject.toml config")
    parser.add_argument("pdf", type=str, help="Input PDF file path")
    parser.add_argument("out", type=str, nargs="?", default=None,
                        help="Output audio file (.mp3 or .wav). If omitted, uses config value.")
    parser.add_argument("--config", type=str, default="pyproject.toml",
                        help="Path to pyproject.toml")
    args = parser.parse_args()

    cfg = load_config(args.config)

    pdf_path = args.pdf
    # Use CLI output path if provided, else fall back to config
    output_path = args.out or cfg.get("paths", {}).get("output", "audiobook.mp3")

    print(f"Input PDF:  {pdf_path}")
    print(f"Output:     {output_path}")

    print(f"Current working directory: {os.getcwd()}")
    # ─── Configure ffmpeg from config ───────────────────────────────
    ffmpeg_cfg = cfg.get("external_tools", {})
    if ffmpeg_path := ffmpeg_cfg.get("ffmpeg"):
        if os.path.isfile(ffmpeg_path):
            print(f"Using ffmpeg: {ffmpeg_path}")
            AudioSegment.converter = ffmpeg_path
            AudioSegment.ffmpeg = ffmpeg_path
        else:
            print(f"Warning: ffmpeg path not found: {ffmpeg_path}")
    if ffprobe_path := ffmpeg_cfg.get("ffprobe"):
        if os.path.isfile(ffprobe_path):
            AudioSegment.ffprobe = ffprobe_path

    # Load TTS
    tts = load_tts(cfg)

    print("Extracting text...")
    raw_text = extract_text_from_pdf(pdf_path)
    text = clean_text(raw_text)
    print(f"Extracted ~{len(text.split())} words.")

    max_words = cfg.get("processing", {}).get("max_words_per_chunk", 350)
    chunks = split_text_into_chunks(text, max_words=max_words)
    print(f"Split into {len(chunks)} chunks.")

    print("Generating audio...")
    audio_segments = []
    pause_sec = cfg.get("processing", {}).get("pause_between_chunks_sec", 0.6)
    pause_ms = int(pause_sec * 1000)

    for chunk in tqdm(chunks, desc="Generating"):
        if not chunk.strip():
            continue
        audio_np, sr = generate_audio_chunk(tts, chunk)
        if len(audio_np) > 0:
            segment = numpy_to_audio_segment(audio_np, sr)
            audio_segments.append(segment)
            audio_segments.append(AudioSegment.silent(duration=pause_ms))

    if not audio_segments:
        print("No audio generated – check input text or TTS model.")
        return

    print("Combining audio...")
    final_audio = sum(audio_segments, AudioSegment.empty())

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = "wav" if out_path.suffix.lower() == ".wav" else "mp3"
    final_audio.export(str(out_path), format=fmt, bitrate="192k" if fmt == "mp3" else None)

    print(f"Audiobook saved: {out_path}")
    print(f"Duration: {len(final_audio)/1000:.1f} seconds")


if __name__ == "__main__":
    main()
