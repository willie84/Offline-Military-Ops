# Offline-Military-Ops

**SCSP Hackathon 2026 · GenAI.mil Track · San Francisco**

The brief: *Build the AI assistant that makes the rank-and-file faster, smarter, and less buried in bureaucracy — and does it offline.*

Most "AI for the military" demos assume reliable connectivity. Real service members operate from moving vehicles, ships at sea, and forward sites where the network is intermittent at best. We took the offline constraint seriously: every component runs on a single laptop with no network, and the system gracefully handles the intermittent connectivity that defines real DDIL (Denied, Degraded, Intermittent, Limited bandwidth) environments.

## Team

- Willie Macharia (solo)

## Track

GenAI.mil

## What we built

A CLI assistant called `oo` (OffGrid Ops) that does three things, all offline:

1. **Regulation Q&A with paragraph-precision citations.** Local RAG over Army Regulations (AR 600-8-10, AR 350-1, AR 670-1). Answers cite to the specific paragraph — *"AR 600-8-10, Para 2-3a(1)"* — not just the document.

2. **Form auto-fill from natural language.** Say *"I need 10 days of leave starting June 3, visiting family in Berkeley"* and the assistant extracts structured fields (validated by Pydantic) and renders a completed DA Form 31 PDF with real fillable form fields.

3. **Store-and-forward dispatch with priority queues.** Filled forms queue locally in a SQLite outbox with priority tiers (URGENT vs ROUTINE). When connectivity returns, the queue drains automatically — a long-running iTerm2 daemon picks up dispatched PDFs and emails them via SMTP to the receiving unit.

The whole stack runs locally: Llama 3.1 8B via Ollama, ChromaDB for vectors, SQLite for the outbox, ReportLab for PDF rendering, pdfrw for fillable form fields. No external API calls during operation, no telemetry, no surprises.

## Demo

1. Toggle macOS Wi-Fi **off** (real airplane mode, not simulated).
2. `oo status` confirms OFFLINE — the system probes the network and detects it.
3. `oo ask "How is ordinary leave accrued?"` returns a cited answer from the offline index.
4. `oo leave -r "10 days starting June 3..."` extracts fields, fills the DA-31 PDF, queues it in the outbox.
5. `oo outbox` shows the pending form with its priority.
6. `oo sync` refuses — no connectivity.
7. Toggle Wi-Fi **on**.
8. `oo sync` drains the queue. The iTerm watcher daemon (running silently in another pane) detects the dispatched PDF within 2 seconds and emails it via AWS WorkMail. The form is delivered.

The whole flow runs in under 4 minutes. The judge sees a real network toggle, real local AI inference, and a real email landing in the receiving inbox.

## Datasets / APIs used

All public, all unclassified, all bulk-downloadable for offline use:

- **Army Publishing Directorate** (https://armypubs.army.mil) — Army Regulations and DA forms:
  - AR 600-8-10 (Leaves and Passes)
  - AR 350-1 (Army Training and Leader Development)
  - AR 670-1 (Wear and Appearance of Army Uniforms and Insignia)
  - DA Form 31 (Request and Authority for Leave) — October 2023 fillable edition

No external runtime APIs. All retrieval and generation happens against a locally-built ChromaDB index. Email delivery uses AWS WorkMail SMTP (configured per deployment).

## Architecture
[Soldier device, offline]                [Conditional: when online]
─────────────────────────                ──────────────────────────
oo ask  ──►  Retriever  ──► ChromaDB     oo sync  ──► drops PDFs
(nomic-embed)    (784 chunks)         in data/dispatch/
↓                                        │
Generator  ──► Llama 3.1 8B                            ↓
(cited answer)                              [iTerm watcher daemon]
│
oo leave  ──► Extractor  ──► Llama 3.1 8B                 ↓
(Pydantic schema)                        AWS WorkMail SMTP
↓                              (S-1 inbox)
Renderer  ──► DA-31 fillable PDF
(pdfrw writes fields directly)
↓
Outbox queue (SQLite)
with priority tier

## How to run it

### Prerequisites

- macOS (tested on Apple Silicon M1/M2/M3)
- Python 3.11+
- ~14 GB free disk space (models + index)
- 16 GB RAM recommended
- Ollama installed (https://ollama.com)
- iTerm2 (for the dispatch watcher daemon)

### One-time setup (requires internet)

```bash
git clone https://github.com/<your-username>/offline-military-ops.git
cd offline-military-ops

# Install local models
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build the vector index from the Army regs in corpus/regs/
python scripts/build_index.py
```

### Configure the dispatch watcher (for email delivery)

Create `~/.offgrid_ops.env`:

```bash
OO_PROJECT_ROOT=/absolute/path/to/offline-military-ops
OO_SMTP_HOST=smtp.mail.us-east-1.awsapps.com
OO_SMTP_PORT=465
OO_SMTP_USER=your-workmail-user@yourorg.awsapps.com
OO_SMTP_PASS=your-workmail-password
OO_RECIPIENT=s1-admin@unit.example.com
```

Then `chmod 600 ~/.offgrid_ops.env`.

Install `scripts/dispatch_watcher.py` as an iTerm2 Long-Running Daemon:
- iTerm → Scripts → New Python Script → Long-Running Daemon
- Save as `dispatch_watcher.py`
- Paste the script content
- Launch from iTerm's Scripts menu before running the demo

### Run the CLI (offline)

```bash
python cli.py status
python cli.py ask "How is ordinary leave accrued?"
python cli.py leave -r "10 days starting June 3, family in Berkeley"
python cli.py outbox
python cli.py sync
```

You can disconnect from the network at any point — `oo ask`, `oo leave`, and `oo outbox` all work offline. Only `oo sync` requires connectivity.

## Why this matters

The Army loses an enormous amount of soldier-time to administrative friction. In garrison that's annoying. In deployed and DDIL environments where connectivity is intermittent, it's a *readiness* problem — soldiers can't file the paperwork that authorizes their actions, can't access the regulations that constrain them, can't pull the rates and dates they're owed. The AI tools that are supposed to fix this assume a connectivity model that doesn't match the operational reality.

This project is a small step toward bringing that capability to where the work actually happens.

## Future work

Cut for time, planned for next iteration:

### Phase 2: Decentralized Mesh Network

The current system assumes a single laptop with intermittent connectivity to the internet. Real DDIL environments have multiple devices operating in the field with no external connectivity whatsoever.

The next iteration will introduce:

- **Device-to-device P2P sync**: Forms sync across a mesh of laptops/phones running the OffGrid Ops daemon. When any device reconnects to the internet, the entire distributed queue drains.
- **Cryptographic provenance**: Each form is signed with the originating device's key. Recipients can verify the chain of custody through the mesh network.
- **Conflict resolution**: If a form is edited on multiple devices, CRDT-based merge logic determines the canonical version without data loss.
- **Bandwidth awareness**: On weak links, only metadata syncs; full PDFs sync when bandwidth improves.

This transforms the system from "one soldier's laptop" to "a unit's distributed office." The architecture is scoped; the single-device foundation ships first.

### Additional forms and workflows

- **DA Form 4187** (Personnel Action) — same extraction/rendering pattern, extends the platform
- **DA Form 3161** (Request for Issue/Turn-In) — supply requisitions for missions
- **Multi-form routing** — NL input routes to the correct form automatically

### Operational enhancements

- **S-1 (admin shop) inbox UI** — receiving inbox with regulation-version validation and approval workflows
- **Voice input** — Whisper-based transcription for hands-busy environments
- **Background daemon** (`offline-mil-d`) — replaces explicit `oo sync` with automatic dispatch on reconnection
- **Regulation-aware validation** — before queueing, system validates leave request against AR 600-8-10 and flags compliance issues with citations

## License

MIT (see LICENSE)

---

## Technical notes

### Why offline-first matters

DDIL (Denied, Degraded, Intermittent, Limited) is a stated DoD priority. This system is built from first principles for environments where:
- Connectivity is sporadic (convoy movement, forward positions)
- Bandwidth is limited (satellite uplinks, HF radio)
- Latency is high (ship at sea, remote FOB)
- Disconnection is expected (EW-contested environment)

Rather than treating offline as an edge case, we treat it as the primary operating mode. The system works fully disconnected and handles reconnection gracefully.

### Deployment considerations

For production deployment:
- Pre-cache models and indices on ruggedized devices before deployment
- Package as a standalone binary (PyInstaller) for non-technical users
- Integrate with military PKI for form signing (Phase 2)
- Add SQLite WAL mode for robustness in field conditions
- Test on older hardware (some forward positions use older laptops)

---

**Built by**: Willie Macharia  
**Hackathon**: SCSP 2026, San Francisco  
**Submission date**: April 26, 2026