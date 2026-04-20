# PDF to Audiobook — Electron + React + Vite

A cross-platform desktop application that converts PDF files to audiobooks using the [Kokoro TTS](https://github.com/hexgrad/kokoro) engine.  
This is a TypeScript/React/Electron rewrite of the original PySide6 application.

---

## Architecture

```
pdf-to-audiobook/
├── electron/
│   ├── main.ts          # Electron main process (IPC handlers, spawn Python)
│   ├── preload.ts       # contextBridge API exposed to renderer
│   ├── configLoader.ts  # Reads pyproject.toml → AppConfig
│   └── queue.ts         # Node.js port of Queue.py / QueueService.py
│
├── src/
│   ├── types/index.ts   # Shared TypeScript types + ElectronAPI interface
│   ├── App.tsx          # Root component (tabs, global IPC listeners)
│   ├── index.css        # Global dark-industrial design system
│   ├── components/
│   │   ├── SingleFileTab.tsx   # Single-file conversion table
│   │   ├── BatchTab.tsx        # Folder-level batch conversion table
│   │   ├── PathInput.tsx       # Browse-button path selector
│   │   ├── ProgressCell.tsx    # Animated progress bar cell
│   │   ├── QueuePanel.tsx      # Persisted queue viewer
│   │   └── StatusBar.tsx       # Bottom status bar
│
├── PDF_to_Audiobook.py  # Python converter (unchanged — called as subprocess)
├── pyproject.toml       # Config file — read by both Python and Electron
└── electron.vite.config.ts
```

---

## Prerequisites

### Node.js
- Node.js **≥ 18** (comes with npm)

### Python environment
The Electron app spawns `PDF_to_Audiobook.py` as a child process.  
Create a virtualenv at `audiobook_env/` next to the project root:

```bash
# Windows
python -m venv audiobook_env
audiobook_env\Scripts\pip install -r requirements.txt

# macOS / Linux
python3 -m venv audiobook_env
audiobook_env/bin/pip install -r requirements.txt
```

`requirements.txt` should contain the same deps as `pyproject.toml`:

```
pypdf>=5.0
nltk>=3.8
tqdm>=4.66
numpy>=1.26
soundfile>=0.12
pydub>=0.25
kokoro>=0.9.4
torch  # install the correct CUDA/CPU wheel for your machine
```

### ffmpeg
Download a static build and extract to `./ffmpeg/bin/` (matching `pyproject.toml`):
- Windows: https://www.gyan.dev/ffmpeg/builds/
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

---

## before anything:

Run:

```
npm install --package-lock-only
``
Which installs package-lock.json without any node modules.

Then run:
```
npm audit
```

Consider output carefully.


## Development

```bash
npm install
source audiobook_env/Scripts/activate
npm run dev
```

This starts Vite dev server + Electron with hot-reload.

---

## Production build

```bash
source audiobook_env/Scripts/activate
npm run build       # compile TypeScript + bundle Vite
npm run package     # wrap with electron-builder (auto-detects platform)

# Or platform-specific:
npm run package:win
npm run package:mac
npm run package:linux
```

Output lands in `release/`.

---

## Configuration

`pyproject.toml` is the single source of truth for both Python and Electron:

| Key | Default | Description |
|-----|---------|-------------|
| `[tool.pdf-to-audiobook.tts] engine` | `kokoro` | TTS engine |
| `[tool.pdf-to-audiobook.tts] voice` | `af_heart` | Default voice |
| `[tool.pdf-to-audiobook.processing] max_words_per_chunk` | `350` | Words per TTS chunk |
| `[tool.pdf-to-audiobook.external_tools] ffmpeg` | `./ffmpeg/bin/ffmpeg.exe` | ffmpeg path |
| `[dropdowns] voices` | (list) | Voices shown in dropdowns |

---

## Queue system

The queue is a folder of JSON files (`queue/<uuid>.json`), one per job.  
This is a direct port of the original `Queue.py` + `QueueService.py` pair.  
Jobs survive app restarts and are shown in the Queue panel at the bottom of the UI.

**Job lifecycle:** `pending → running → completed | error`

---

## IPC Channels

| Channel | Direction | Description |
|---------|-----------|-------------|
| `config:load` | invoke | Load `pyproject.toml` |
| `dialog:openFile` | invoke | Native open-file dialog |
| `dialog:saveFile` | invoke | Native save-file dialog |
| `dialog:openDir` | invoke | Native open-directory dialog |
| `queue:add` | invoke | Persist a new job |
| `queue:getAll` | invoke | Read all jobs |
| `queue:remove` | invoke | Delete a job file |
| `queue:clear` | invoke | Delete all job files |
| `conversion:start` | invoke | Spawn Python for single file |
| `conversion:startBatch` | invoke | Spawn Python for folder |
| `conversion:progress` | main→renderer | Progress update (0-100) |
| `conversion:complete` | main→renderer | Job finished |
| `conversion:error` | main→renderer | Job failed |
| `queue:changed` | main→renderer | Queue state changed |
| `file:play` | invoke | Play audio with ffplay |
| `file:open` | invoke | Open file/folder with OS |
