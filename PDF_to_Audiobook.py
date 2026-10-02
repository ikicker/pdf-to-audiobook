"""
PDF to Audiobook Converter - OOP Version
Can be imported and used externally
"""

import argparse
import tomllib
import os
import sys
from pathlib import Path
import numpy as np
from tqdm import tqdm
from pydub import AudioSegment
import nltk
from nltk.tokenize import sent_tokenize
from html.parser import HTMLParser
from html import unescape
from pypdf import PdfReader
import torch

# Input formats this converter can read. Output is chosen by the output suffix (.wav or .mp3).
SUPPORTED_INPUT_EXTENSIONS = {".pdf", ".epub", ".txt", ".text", ".md"}
SUPPORTED_OUTPUT_EXTENSIONS = {".wav", ".mp3"}

nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)


class AudiobookConverter:
    def __init__(self, config_path: str = "pyproject.toml", device: str = None):
        self.config = self._load_config(config_path)
        self._setup_ffmpeg()

        # Resolve device: explicit arg > config file > default "cpu"
        self.device = device or self.config.get("tts", {}).get("device", "cpu")

        if self.device == "cpu":
            # Force CPU *before* any CUDA context can be created. Some libs
            # (kokoro included) probe torch.cuda.is_available() internally
            # regardless of a device kwarg, so hiding the GPU from the
            # process is the only reliable way to guarantee no CUDA/cuDNN
            # init is attempted. Necessary on GPUs below SM 7.5 (e.g. GTX
            # 900/Maxwell series), which recent cuDNN releases no longer
            # support.
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
        print(f"🖥️  Using device: {self.device}")

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from pyproject.toml"""
        if not os.path.isfile(config_path):
            print(f"Warning: Config file {config_path} not found. Using defaults.", file=sys.stderr)
            return {}

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
            return data.get("tool", {}).get("pdf-to-audiobook", {})
        except Exception as e:
            print(f"Error loading config from {config_path}: {e}", file=sys.stderr)
            return {}

    def _setup_ffmpeg(self):
        """Set up pydub with ffmpeg path from config"""
        ffmpeg_cfg = self.config.get("external_tools", {})
        ffmpeg_path = ffmpeg_cfg.get("ffmpeg")
        ffprobe_path = ffmpeg_cfg.get("ffprobe")

        if ffmpeg_path and os.path.isfile(ffmpeg_path):
            AudioSegment.converter = ffmpeg_path
            AudioSegment.ffmpeg = ffmpeg_path
            print(f"✅ Using ffmpeg: {ffmpeg_path}")
        if ffprobe_path and os.path.isfile(ffprobe_path):
            AudioSegment.ffprobe = ffprobe_path

    def pdf_to_audio(self, pdf_path: str, output_path: str = None, voice: str = None):
        """
        Convert a PDF, EPUB, or plain-text file to an audiobook.
        Can be called externally after importing the class.

        The method name is kept for compatibility with the Electron UI and
        older callers. `pdf_path` may be a .pdf, .epub, .txt, .text, or .md file.

        Args:
            pdf_path (str): Path to the input PDF, EPUB, or plain-text file
            output_path (str, optional): Output audio file path (.mp3 or .wav). Defaults to config value.
            voice (str, optional): Voice to use (e.g. "af_heart", "am_adam"). Defaults to config value.
        """
        # Use defaults from config if not provided
        if output_path is None:
            output_path = self.config.get("paths", {}).get("output", "audiobook.mp3")
        if voice is None:
            voice = self.config.get("tts", {}).get("voice", "af_heart")

        self.pdf_path = pdf_path
        self.output_path = output_path
        self.voice = voice

        print(f"\nStarting conversion:")
        print(f"   Input:   {self.pdf_path}")
        print(f"   Output:  {self.output_path}")
        print(f"   Voice:   {self.voice}\n")

        # Load TTS engine
        self._load_tts()

        # Extract and process text
        print(f"Extracting text from {Path(self.pdf_path).suffix.lower() or 'input'}...")
        raw_text = self._extract_text()
        text = self._clean_text(raw_text)
        if not text.strip():
            raise ValueError(f"No readable text extracted from {self.pdf_path}")
        print(f"Extracted ~{len(text.split())} words.")

        max_words = self.config.get("processing", {}).get("max_words_per_chunk", 350)
        chunks = self._split_into_chunks(text, max_words)
        print(f"Split into {len(chunks)} chunks.")

        # Generate audio
        print("Generating audio...")
        audio_segments = []
        pause_sec = self.config.get("processing", {}).get("pause_between_chunks_sec", 0.6)
        pause_ms = int(pause_sec * 1000)
        pause = self._silence(pause_ms, sample_rate=24000)

        for chunk in tqdm(chunks, desc="Generating"):
            if not chunk.strip():
                continue
            audio_np, sr = self._generate_audio_chunk(chunk)
            if len(audio_np) > 0:
                segment = self._numpy_to_audio_segment(audio_np, sr)
                audio_segments.append(segment)
                if pause_ms > 0:
                    audio_segments.append(pause if pause.frame_rate == sr else self._silence(pause_ms, sr))

        if not audio_segments:
            print("❌ No audio generated.")
            return

        print("Combining audio...")
        final_audio = sum(audio_segments, AudioSegment.empty())

        # Save final file. Extension selects the container: .wav (lossless) or .mp3.
        out_path = Path(self.output_path)
        if out_path.suffix.lower() not in SUPPORTED_OUTPUT_EXTENSIONS:
            if out_path.suffix == "":
                out_path = out_path.with_suffix(".mp3")
            else:
                raise ValueError(
                    f"Unsupported output format '{out_path.suffix}'. Use .wav or .mp3."
                )
        out_path.parent.mkdir(parents=True, exist_ok=True)

        fmt = "wav" if out_path.suffix.lower() == ".wav" else "mp3"
        export_kwargs = {"format": fmt}
        if fmt == "mp3":
            export_kwargs["bitrate"] = "192k"
        final_audio.export(str(out_path), **export_kwargs)

        print(f"\n✅ Success! Audiobook saved to: {out_path}")
        print(f"   Duration: {len(final_audio)/1000:.1f} seconds")
        return final_audio

    def convert(self, input_path: str = None, output_path: str = None, voice: str = None, pdf_path: str = None, **kwargs):
        """
        Public entry point used by the UI and external callers.

        `pdf_to_audio` remains as an alias. Accepts either name for the source
        file so older and newer call sites both work.
        """
        source = input_path or pdf_path or kwargs.get("input_file") or kwargs.get("file")
        if not source:
            raise TypeError("convert() requires input_path or pdf_path")
        output = output_path or kwargs.get("output_file") or kwargs.get("out")
        selected_voice = voice if voice is not None else kwargs.get("voice")
        return self.pdf_to_audio(pdf_path=source, output_path=output, voice=selected_voice)

    # ==================== Internal Helper Methods ====================

    def _load_tts(self):
        tts_section = self.config.get("tts", {})
        engine = tts_section.get("engine", "kokoro").lower()

        if engine == "kokoro":
            from kokoro import KPipeline
            lang_code = tts_section.get("language_code", "a")

            try:
                # Newer kokoro versions accept a device kwarg directly.
                pipeline = KPipeline(lang_code=lang_code, device=self.device)
            except TypeError:
                # Older versions don't accept device= at all; CUDA is
                # already hidden via CUDA_VISIBLE_DEVICES above, so this
                # will fall back to CPU on its own.
                pipeline = KPipeline(lang_code=lang_code)

            self.tts = {
                "engine": "kokoro",
                "pipeline": pipeline,
                "voice": self.voice,
                "sr": 24000
            }
        else:
            raise ValueError(f"Unsupported TTS engine: {engine}")

    def _extract_text(self) -> str:
        path = Path(self.pdf_path)
        if not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")

        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_INPUT_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_INPUT_EXTENSIONS))
            raise ValueError(
                f"Unsupported input format '{suffix or '(none)'}'. Use one of: {supported}."
            )
        if suffix == ".pdf":
            return self._extract_pdf(path)
        if suffix == ".epub":
            return self._extract_epub(path)
        return self._extract_plain_text(path)

    def _extract_pdf(self, path: Path) -> str:
        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n\n"
        return text.strip()

    def _extract_plain_text(self, path: Path) -> str:
        raw = path.read_bytes()
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            return raw.decode("utf-16")
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")

    def _extract_epub(self, path: Path) -> str:
        try:
            import ebooklib
            from ebooklib import epub
        except ImportError as exc:
            raise ImportError(
                "EPUB support requires ebooklib. Install it with: pip install ebooklib"
            ) from exc

        book = epub.read_epub(str(path), options={"ignore_ncx": True})
        documents = []
        seen = set()
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            name = (item.get_name() or "").replace("\\", "/").lower()
            base = name.rsplit("/", 1)[-1]
            # Skip navigation documents; they repeat the table of contents.
            if base in {"nav.xhtml", "nav.html", "toc.xhtml", "toc.html", "toc.ncx"}:
                continue
            seen.add(item.get_id())
            documents.append(item)

        # Prefer spine order when the spine points at documents we kept.
        ordered = []
        id_to_item = {item.get_id(): item for item in documents}
        spine_ids = [entry[0] for entry in getattr(book, "spine", []) or []]
        for idref in spine_ids:
            item = id_to_item.get(idref)
            if item is not None:
                ordered.append(item)
        if not ordered:
            ordered = documents

        parts = []
        for item in ordered:
            content = item.get_content()
            if isinstance(content, bytes):
                html = content.decode("utf-8", errors="replace")
            else:
                html = str(content or "")
            chapter = _html_to_text(html).strip()
            if chapter:
                parts.append(chapter)
        return "\n\n".join(parts).strip()

    def _clean_text(self, text: str) -> str:
        lines = text.splitlines()
        cleaned = [line.strip() for line in lines if line.strip() and not line.strip().isdigit()]
        return " ".join(cleaned).replace("  ", " ")

    def _split_into_chunks(self, text: str, max_words: int = 350) -> list[str]:
        sentences = sent_tokenize(text)
        chunks = []
        current = []
        count = 0

        for sentence in sentences:
            words = len(sentence.split())
            if count + words > max_words and current:
                chunks.append(" ".join(current))
                current = []
                count = 0
            current.append(sentence)
            count += words

        if current:
            chunks.append(" ".join(current))
        return chunks

    def _generate_audio_chunk(self, text_chunk: str):
        if self.tts["engine"] == "kokoro":
            audio_pieces = []
            for _, _, audio in self.tts["pipeline"](text_chunk, voice=self.tts["voice"]):
                if len(audio) > 0:
                    audio_pieces.append(audio)
            if audio_pieces:
                return np.concatenate(audio_pieces), self.tts["sr"]
            return np.array([]), self.tts["sr"]

    def _numpy_to_audio_segment(self, audio_array: np.ndarray, sample_rate: int) -> AudioSegment:
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

    def _silence(self, duration_ms: int, sample_rate: int = 24000) -> AudioSegment:
        """Build a silent segment. Does not use AudioSegment.silent (11025 Hz default)."""
        if AudioSegment is None:
            raise RuntimeError("pydub AudioSegment is not available; install pydub and ffmpeg.")
        frames = int(sample_rate * (duration_ms / 1000.0))
        return AudioSegment(
            data=b"\x00\x00" * frames,
            sample_width=2,
            frame_rate=sample_rate,
            channels=1,
        )



class _HTMLTextExtractor(HTMLParser):
    """Pull visible text out of an EPUB chapter, keeping paragraph breaks."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self._skip += 1
        if tag in {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "blockquote"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1
        if tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "blockquote"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip and data:
            self.parts.append(data)


def _html_to_text(html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html or "")
    parser.close()
    text = unescape("".join(parser.parts))
    lines = [" ".join(line.split()) for line in text.splitlines()]
    cleaned = []
    blank = False
    for line in lines:
        if not line:
            if not blank and cleaned:
                cleaned.append("")
            blank = True
            continue
        cleaned.append(line)
        blank = False
    return "\n".join(cleaned).strip()


# ====================== CLI Entry Point ======================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a PDF, EPUB, or plain-text file to an MP3 or WAV audiobook"
    )
    parser.add_argument(
        "pdf",
        type=str,
        nargs="?",
        help="Path to input PDF, EPUB, or plain text (.txt, .text, .md)",
    )
    parser.add_argument("out", type=str, nargs="?", help="Output audio file (.mp3 or .wav)")
    parser.add_argument("--voice", type=str, help="Voice to use (e.g. af_heart, am_adam)")
    parser.add_argument(
        "--device",
        type=str,
        choices=["cpu", "cuda"],
        default="cpu",
        help="Compute device for TTS inference (default: cpu). "
             "Use cuda only on GPUs with compute capability >= 7.5.",
    )
    args = parser.parse_args()

    converter = AudiobookConverter(device=args.device)

    if args.pdf:
        # CLI mode
        converter.convert(input_path=args.pdf, output_path=args.out, voice=args.voice)
    else:
        # Interactive mode
        converter.pdf_to_audio(
            pdf_path=input("Enter PDF, EPUB, or text path: ").strip(),
            output_path=input("Enter output filename: ").strip() or None,
            voice=input("Enter voice (e.g. af_heart): ").strip() or None
        )