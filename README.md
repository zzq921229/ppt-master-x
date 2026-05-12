# PPT Master — AI generates natively editable PPTX from any document

[![Version](https://img.shields.io/badge/version-v2.6.0-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Drop in a PDF, DOCX, URL, or Markdown — get back a **natively editable PowerPoint** with real shapes, real text boxes, and real charts. Not images. Click anything and edit it.

> **How it works** — PPT Master is a workflow (a "skill") that works inside AI IDEs like Claude Code, Cursor, VS Code + Copilot, or Codebuddy. You chat with the AI — "make a deck from this PDF" — and it follows the workflow to produce a real editable `.pptx` on your computer. No coding on your side; the IDE is just where the conversation happens.
>
> **What you'll do**: install Python, install an AI IDE, drop in your material.

PPT Master is different:

- **Real PowerPoint** — if a file can't be opened and edited in PowerPoint, it shouldn't be called a PPT. Every element PPT Master outputs is directly clickable and editable
- **Transparent, predictable cost** — the tool is free and open source; the only cost is your AI model usage
- **Data stays local** — your files shouldn't have to be uploaded to someone else's server just to make a presentation. Apart from AI model communication, the entire pipeline runs on your machine
- **No platform lock-in** — your workflow shouldn't be held hostage by any single company. Works with Claude Code, Cursor, VS Code Copilot, and more; supports Claude, GPT, Gemini, Kimi, and other models

AI presentation tools roughly fall into four categories. PPT Master only does the last one:

| Category | Output | Editable element-by-element in PowerPoint? |
|---|---|:---:|
| Template fill-in | PPTX built from a fixed template | Partially — limited by the template |
| Image-based | One large image per slide, packed into PPTX | ❌ each slide is a picture |
| HTML presentation | Web-based deck | ❌ not a PPTX |
| **Native editable (PPT Master)** | **Real DrawingML shapes, text boxes, charts** | ✅ click any element to edit |

---

## Gallery

<table>
  <tr>
    <td align="center"><img src="docs/assets/screenshots/preview_magazine_garden.png" alt="Magazine style — Garden building guide" /><br/><sub><b>Magazine</b> — warm earthy tones, photo-rich layout</sub></td>
    <td align="center"><img src="docs/assets/screenshots/preview_academic_medical.png" alt="Academic style — Medical image segmentation research" /><br/><sub><b>Academic</b> — structured research format, data-driven</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/assets/screenshots/preview_dark_art_mv.png" alt="Dark art style — Music video analysis" /><br/><sub><b>Dark Art</b> — cinematic dark background, gallery aesthetic</sub></td>
    <td align="center"><img src="docs/assets/screenshots/preview_nature_wildlife.png" alt="Nature style — Wildlife wetland documentary" /><br/><sub><b>Nature Documentary</b> — immersive photography, minimal UI</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/assets/screenshots/preview_tech_claude_plans.png" alt="Tech style — Claude AI subscription plans" /><br/><sub><b>Tech / SaaS</b> — clean white cards, pricing table layout</sub></td>
    <td align="center"><img src="docs/assets/screenshots/preview_launch_xiaomi.png" alt="Product launch style — Xiaomi spring release" /><br/><sub><b>Product Launch</b> — high contrast, bold specs highlight</sub></td>
  </tr>
</table>

---

## Quick Start

### 1. Prerequisites

**You only need Python.** Everything else is installed via `pip install -r requirements.txt`.

| Dependency | Required? | What it does |
|------------|:---------:|--------------|
| [Python](https://www.python.org/downloads/) 3.10+ | ✅ **Yes** | Core runtime — the only thing you actually need to install |

> **TL;DR** — Install Python, run `pip install -r requirements.txt`, and you're ready to generate presentations.

<details open>
<summary><strong>Windows</strong> — see the dedicated step-by-step guide ⚠️</summary>

Windows requires a few extra steps (PATH setup, execution policy, etc.). We wrote a **step-by-step guide** specifically for Windows users:

**📖 [Windows Installation Guide](./docs/windows-installation.md)** — from zero to a working presentation in 10 minutes.

Quick version: download Python from [python.org](https://www.python.org/downloads/) → **check "Add to PATH"** during install → `pip install -r requirements.txt` → done.
</details>

<details>
<summary><strong>macOS / Linux</strong> — install and go</summary>

```bash
# macOS
brew install python
pip install -r requirements.txt

# Ubuntu / Debian
sudo apt install python3 python3-pip
pip install -r requirements.txt
```
</details>

<details>
<summary><strong>Edge-case fallback</strong> — 99% of users don't need this</summary>

**Pandoc** — only needed for legacy document formats: `.doc`, `.odt`, `.rtf`, `.tex`, `.rst`, `.org`, or `.typ`. `.docx`, `.html`, `.epub`, `.ipynb` are handled natively by Python — no pandoc required.

```bash
# macOS
brew install pandoc

# Ubuntu / Debian
sudo apt install pandoc
```
</details>

### 2. Pick an Agent

PPT Master runs in **any tool with agent capability** — read/write files, execute commands, and sustain multi-turn conversation.

| Type | Examples | Notes |
|---|---|---|
| **IDE-native agent** | • VS Code architecture ([VS Code](https://code.visualstudio.com/) itself, plus forks & derivatives): [Cursor](https://cursor.sh/), Trae, Codebuddy IDE, [Windsurf](https://codeium.com/windsurf), Void, etc.<br>• Other architectures: [Zed](https://zed.dev/), etc. | Editor with a built-in agent |
| **IDE plugin / extension** | [GitHub Copilot](https://github.com/features/copilot), [Claude Code](https://claude.ai/code) (VS Code / JetBrains extension), [Cline](https://cline.bot/), [Continue](https://continue.dev/), Roo Code, etc. | Installed inside hosts like VS Code or JetBrains |
| **CLI agent** | [Claude Code](https://claude.ai/code) CLI, [Codex CLI](https://github.com/openai/codex), [Aider](https://aider.chat/), Gemini CLI, etc. | Runs in the terminal; suits scripting, remote, or server use |

> **Model recommendation**: prefer **Claude Opus / Sonnet** with a large context window and `gpt-image-2` for images.

### 3. Set Up

**Option A — Download ZIP** (no Git required): click **Code → Download ZIP** on this page, then unzip.

**Option B — Git clone** (requires [Git](https://git-scm.com/downloads) installed):

```bash
git clone https://github.com/zzq921229/ppt-master-x.git
cd ppt-master-x
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

To update later (Option A / B): `python3 skills/ppt-master/scripts/update_repo.py`

### 4. Create

**Provide source materials (recommended):** Place your PDF, DOCX, images, or other files in the `projects/` directory, then tell the AI chat panel which files to use. The quickest way to get the path: right-click the file in your file manager or IDE sidebar → **Copy Path** (or **Copy Relative Path**) and paste it directly into the chat.

```
You: Please create a PPT from projects/q3-report/sources/report.pdf
```

**Paste content directly:** You can also paste text content straight into the chat window and the AI will generate a PPT from it.

```
You: Please turn the following into a PPT: [paste your content here...]
```

**Template selection (interactive):** If you don't specify a template in your first message, the AI will ask:

```
AI:  Do you want to use a built-in template? Available options:
     - academic_defense  (thesis defense, academic reports)
     - google_style      (annual reports, tech sharing)
     - government_red    (government briefings)
     - government_blue   (government briefings, modern style)
     - mckinsey          (consulting, executive briefings)
     - exhibit           (strategic planning, board presentations)
     - smart_red         (product launches, solution presentations)
     - pixel_retro       (tech talks, geek style)
     - ... (and more)
     Reply with a template name, or say "no" for free design.
```

You can also proactively request a template:

```
You: Please create a PPT using the google_style template
```

Or use the built-in CLI helper to list all templates:

```bash
python3 skills/ppt-master/scripts/project_manager.py list-templates
```

And initialize a project with a template directly:

```bash
python3 skills/ppt-master/scripts/project_manager.py init my_deck --format ppt169 --template google_style
```

Either way, the AI will first confirm the design spec:

```
AI:  Sure. Let's confirm the design spec:
     [Template] google_style
     [Format]   PPT 16:9
     [Pages]    8-10 pages
     ...
```

The AI handles everything — content analysis, visual design, SVG generation, and PPTX export.

> **Output:** Main native-shapes `.pptx` (directly editable) saved to `exports/<name>_<timestamp>.pptx`. The SVG snapshot `_svg.pptx` and a copy of `svg_output/` are archived to `backup/<timestamp>/` for visual reference and pptx rebuild without re-running the LLM. Requires Office 2016+.

> **AI lost context?** Ask it to read `skills/ppt-master/SKILL.md`.

> **Something went wrong?** Check the **[FAQ](./docs/faq.md)** — it covers model selection, layout issues, export problems, and more.

### 5. Image Acquisition (Optional)

Two paths for non-user images, mixable per row in the same deck:

For API-backed features, put credentials in `.env`. Clone installs can use `cp .env.example .env`; skill marketplace installs should use a persistent user config:

```bash
mkdir -p ~/.ppt-master
cp /path/to/installed/ppt-master-x/.env.example ~/.ppt-master/.env
```

PPT Master reads the current process environment first, then the first `.env` found in this order: current working directory, clone repo root, `~/.ppt-master/.env`.

**A) AI generation** — `image_gen.py`. Set `IMAGE_BACKEND` plus the provider's `*_API_KEY` (`OPENAI_API_KEY`, `GEMINI_API_KEY`, etc.), and the pipeline calls it automatically. Run `python3 skills/ppt-master/scripts/image_gen.py --list-backends` for the full backend list. `gpt-image-2` is currently the best default.

**B) Web image search** — `image_search.py`. **Zero-config works**, but configure `PEXELS_API_KEY` / `PIXABAY_API_KEY` (both free) for higher-quality results. Without keys, search uses Openverse / Wikimedia Commons only; this is useful as a fallback, but image quality can be uneven because many results are ordinary user uploads. With keys, the default provider chain also appends Pexels / Pixabay, which materially improves modern stock photography, people, workplace, lifestyle, and illustration coverage.

> Full reference: [`image-generator.md`](./skills/ppt-master/references/image-generator.md) (AI) · [`image-searcher.md`](./skills/ppt-master/references/image-searcher.md) (web).

---

## Documentation

| | Document | Description |
|---|----------|-------------|
| 🪟 | [Windows Installation](./docs/windows-installation.md) | Step-by-step setup guide for Windows users |
| 📖 | [SKILL.md](./skills/ppt-master/SKILL.md) | Core workflow and rules |
| 🎨 | [Templates Guide](./docs/templates-guide.md) | Use, derive, and template boundaries |
| 📐 | [Canvas Formats](./skills/ppt-master/references/canvas-formats.md) | PPT 16:9, Xiaohongshu, WeChat, and 10+ formats |
| 🎬 | [Animations & Transitions](./skills/ppt-master/references/animations.md) | Page transitions and per-element entrance animations |
| 🎙️ | [Audio Narration & Video Export](./docs/audio-narration.md) | TTS narration in 90+ locales, embed audio, export as MP4 |
| 🛠️ | [Scripts & Tools](./skills/ppt-master/scripts/README.md) | All scripts and commands |
| 💼 | [Examples](./examples/README.md) | Example projects and pages |
| 🏗️ | [Technical Design](./docs/technical-design.md) | Architecture, design philosophy, why SVG |
| ❓ | [FAQ](./docs/faq.md) | Model selection, cost, layout troubleshooting, custom templates |

## License

[MIT](LICENSE)
