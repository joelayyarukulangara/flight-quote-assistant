# Flight Quote Assistant

A local Windows desktop app for a tours &amp; travel business that automates
flexible flight fare searching for **package tour quotations** — where the
onward (UP) flight and return (DOWN) flight are often different routes
(e.g. UP: COK → DXB, DOWN: AUH → COK).

Instead of showing 50 confusing one-way results, it searches both legs
across a valid date window, combines them into complete UP+DOWN packages,
applies your filters, and shows only the **best 4 quote-ready options**.

Works fully offline with realistic mock flight data — no API key required
to try it out. SerpAPI (Google Flights) can be added later for live fares,
and OpenAI can optionally be added for polished customer-facing quote
wording (AI is never used to invent fares).

## What it does

- Separate manual entry for UP/Onward and DOWN/Return routes (never assumes
  return = destination → origin)
- Package duration rules (e.g. "4 Days / 3 Nights") that generate only
  valid UP/DOWN date pairs, with optional ± day flexibility
- Rule-based filtering (stops, layovers, baggage, blocked airlines, etc.)
  and ranking into 4 categories: Cheapest, Lowest-stop, Best timing, Best
  value
- Markup / commercial rules per person, with rounding
- Local SQLite caching of searches (default 60 minutes) with a manual
  "Refresh Price" option
- Export: WhatsApp-ready text, PDF quote, Excel comparison sheet
- Saved Quotes tab: search, reopen, re-export, refresh price, delete
- Settings tab: SerpAPI key, OpenAI key (both optional, masked, stored
  locally — never hardcoded), defaults, AI options
- Optional AI summary (OpenAI) that only rewrites the already-selected best
  4 options into clean customer wording — it never searches fares itself

## System requirements

### For staff running the packaged EXE (`FlightQuoteAssistant.exe`)

No Python, no installer, no admin rights needed — just a folder to run it
from.

| | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 (64-bit), version 1809+ | Windows 10/11 (64-bit) |
| CPU | Any 64-bit Intel/AMD CPU from the last ~10 years | — |
| RAM | 4 GB | 8 GB+ (more if many other apps are open) |
| Disk space | ~150 MB free (EXE ~30 MB + room for the SQLite cache/saved quotes, which grow slowly — a few KB per quote) | 500 MB+ |
| Display | 1280×800 | 1366×768 or larger (the form scrolls, so smaller screens still work, just with more scrolling) |
| Internet | **Not required** — mock mode works fully offline | Required only if using live SerpAPI fares or the optional OpenAI quote wording |
| Permissions | Standard (non-admin) user account; write access to the folder the EXE sits in (to create its `data\` subfolder) | — |
| .NET / runtimes | None needed — PyInstaller bundles the Python runtime and all dependencies into the EXE | — |
| Architecture note | This build is 64-bit only. It will not run on 32-bit Windows. | — |

Not supported: Windows 7/8.1 (Python 3.11's own binaries no longer
support them), macOS, or Linux — this build targets Windows specifically
per the project brief.

### For building from source / development

| | Requirement |
|---|---|
| OS | Windows 10/11 (64-bit) — to produce a Windows EXE, PyInstaller must be run *on Windows* (no cross-compiling from macOS/Linux) |
| Python | 3.11 or newer (64-bit), with pip |
| Disk space | ~500 MB for the virtual environment + dependencies, plus ~100 MB temporary space during a PyInstaller build |
| Internet | Required once, to `pip install -r requirements.txt`; not needed afterward for mock-mode development |

## 1. Install Python

Install **Python 3.11+** from https://www.python.org/downloads/ (tick
"Add Python to PATH" during install). Verify with:

```
python --version
```

## 2. Create a virtual environment

```
python -m venv venv
```

Activate it (Windows):

```
venv\Scripts\activate
```

## 3. Install dependencies

```
pip install -r requirements.txt
```

## 4. Run the app

```
python main.py
```

On first run the app creates a local SQLite database at
`data\flight_quote_assistant.db` and defaults to **mock mode**, so you can
use every feature immediately without any API key.

## 5. Using mock mode

Mock mode is enabled by default (Settings tab → "Enable mock mode"). It
generates varied, realistic sample fares (direct, 1-stop, cheap with a long
layover, premium airline, late-night, and an example airline useful for
testing the "blocked airline" filter) so you can fully test searches,
filters, ranking, exports, and saved quotes offline.

## 6. Choosing a flight data provider (for live fares)

The **Settings** tab has a "Flight data source" dropdown:

- **Mock (sample data)** — default; realistic offline sample fares.
- **SerpAPI (Google Flights)** — get a key from https://serpapi.com/,
  paste it into "SerpAPI API key".
- **SearchAPI (Google Flights)** — get a key from https://www.searchapi.io/,
  paste it into "SearchAPI API key".

Pick the provider, paste that provider's key, click **Save Settings**.

**Can any flight API be added just with a key?** Not automatically —
unlike LLMs (below), there's no universal flight-API standard: each
vendor has different authentication, request parameters, and response
shapes. But the app's provider architecture (`providers/base.py`) makes
each new integration a single small adapter file (~100 lines; see
`providers/searchapi_provider.py` for a template). Amadeus, Duffel, Kiwi
etc. can be added the same way.

If the selected provider's key is **missing entirely**, the app falls
back to mock data and shows a warning, since there's no live option
available at all. But once a key **is** configured, a failed live request
never silently substitutes mock data — showing fake fares as if they were
real quotes would be worse than showing nothing. Instead the search stops
with a clear error explaining what failed (invalid route/airport code,
bad key, quota exceeded, network issue, etc.) so you always know whether
you're looking at real fares or not. The app still never crashes on a bad
API response.

## 7. Adding an LLM key (optional, for AI quote wording)

The AI quote wording works with **any LLM provider that exposes an
OpenAI-compatible endpoint** — which is nearly all of them: OpenAI, Groq,
Mistral, DeepSeek, OpenRouter, Together, Google Gemini, and even local
Ollama. Switching providers is just: key + base URL + model name.

1. Get an API key from your chosen LLM provider.
2. In **Settings → AI Quote Wording**: paste the key, pick a provider
   preset (which fills in the base URL — or paste any OpenAI-compatible
   base URL manually), enter one of that provider's model names (e.g.
   `gpt-4o-mini` for OpenAI, `llama-3.3-70b-versatile` for Groq), tick
   "Enable AI summary", then **Save Settings**.
3. In the **Results** tab, click **Generate AI Quote** to produce
   customer-ready wording for the best 4 options (copied to clipboard).

This is entirely optional. Without a key, the app uses a rule-based quote
template automatically and works fully. The LLM is only called when you
click "Generate AI Quote" — never automatically after a search, to control
cost — and it never fetches or invents fares; it only rewords results the
flight provider already returned.

## 8. Build a Windows EXE

With the virtual environment activated, run:

```
pyinstaller --noconfirm --onefile --windowed --name "FlightQuoteAssistant" --collect-all customtkinter --hidden-import PIL._tkinter_finder main.py
```

Flag reference:

| Flag | Why it's needed |
|---|---|
| `--onefile` | Bundles everything into a single `.exe` — easiest to hand to staff |
| `--windowed` | No console window pops up behind the app |
| `--name` | Controls the output filename (`FlightQuoteAssistant.exe`) |
| `--collect-all customtkinter` | CustomTkinter ships JSON theme files that a plain build misses, causing a blank/broken window |
| `--hidden-import PIL._tkinter_finder` | Ensures Pillow's Tk image support is bundled |

This produces `dist\FlightQuoteAssistant.exe` (roughly 25–30 MB) and a
`FlightQuoteAssistant.spec` file in the project root. Keep the `.spec`
file — future rebuilds can just run `pyinstaller FlightQuoteAssistant.spec`
instead of retyping the full command.

**Important — database location:** `config.py` detects when it's running
as a frozen EXE (`sys.frozen`) and stores the SQLite database in a `data`
folder next to the **EXE itself**, not inside PyInstaller's temporary
extraction folder. This means settings, cached searches, and saved quotes
correctly persist between runs. Don't move the `.exe` without also moving
its `data` folder if you want to keep existing saved quotes.

You can safely delete the `build\` folder after a build — it's just
PyInstaller's intermediate working directory and isn't needed to run the
EXE.

## 9. Building a macOS version

This project was built primarily as a Windows desktop app, but the code
has no Windows-specific dependencies (CustomTkinter, Tkinter, sqlite3,
ReportLab, OpenPyXL, requests, and openai all run on macOS), so a Mac
build is possible.

**PyInstaller cannot cross-compile** — it can only build for the OS it's
actually running on. You can't produce a macOS app from Windows (or vice
versa). This repo includes a GitHub Actions workflow at
[.github/workflows/build-macos.yml](.github/workflows/build-macos.yml)
that builds it for you on GitHub's macOS runners, so no physical Mac is
required.

### Triggering the macOS build

1. Push this repo to GitHub (create an empty repo there, then):
   ```
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
2. The workflow runs automatically on every push to `main`, or trigger it
   manually from the repo's **Actions** tab → "Build macOS app" → **Run
   workflow**.
3. It builds two separate `.app` bundles — one for Apple Silicon
   (arm64, `macos-14` runner) and one for Intel Macs (x86_64, `macos-13`
   runner) — since a single PyInstaller run only targets the architecture
   of the machine it's built on.
4. Once the run finishes, download the zipped `.app` from the **Artifacts**
   section of that workflow run and unzip it on a Mac.

### Building manually on a Mac (if you have one)

Same idea as the Windows build, run in Terminal:

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pyinstaller --noconfirm --windowed --name "FlightQuoteAssistant" \
    --collect-all customtkinter --hidden-import PIL._tkinter_finder main.py
```

Note: unlike the Windows build, this intentionally omits `--onefile` —
for macOS `.app` bundles, `--onefile` is discouraged (slower startup,
more Gatekeeper friction) since `--windowed` alone already produces a
proper self-contained `dist/FlightQuoteAssistant.app`.

### macOS distribution notes (Gatekeeper)

macOS is stricter than Windows about unsigned apps. Since this build
isn't code-signed or notarized with an Apple Developer account, the first
time someone opens it they'll likely see **"FlightQuoteAssistant.app
cannot be opened because the developer cannot be verified"**. To open it
anyway:

- Right-click (or Control-click) the app → **Open** → confirm **Open** in
  the dialog (this only needs to be done once per Mac), or
- If it's still blocked, run in Terminal: `xattr -cr /path/to/FlightQuoteAssistant.app`
  to clear the quarantine flag Gatekeeper adds to anything downloaded
  from the internet.

To remove this warning entirely for staff, you'd need an Apple Developer
Program membership ($99/year) to code-sign and notarize the app — optional,
not required for the app to function.

## 10. Distributing the app to travel agency staff

The EXE is fully self-contained — staff machines need **no Python
install** and **no internet access** to run it in mock mode.

### What to hand out

Give each staff member either:

- Just `FlightQuoteAssistant.exe` (simplest — a `data` folder is created
  automatically next to it on first run), or
- A folder containing `FlightQuoteAssistant.exe` plus a pre-populated
  `data\flight_quote_assistant.db` if you want everyone to start with the
  same saved Settings (e.g. your company name, a shared SerpAPI key).

Recommended distribution methods, easiest first:

1. **Shared network drive / folder** — copy `FlightQuoteAssistant.exe`
   into a shared folder each staff PC can reach, and have them copy it
   locally (running EXEs directly off a slow network share works but
   feels sluggish; a local copy is smoother).
2. **Zip file over email / chat / USB** — zip the EXE (optionally with a
   pre-set `data` folder), send it, staff unzip to a folder like
   `C:\FlightQuoteAssistant\`.
3. **Internal software deployment tool** (Intune, PDQ Deploy, GPO
   startup script, etc.) if your IT team already manages installs this
   way — just point it at the `.exe`, no installer/MSI is required since
   PyInstaller's `--onefile` output runs standalone.

### Installing on a staff PC

1. Create a folder, e.g. `C:\FlightQuoteAssistant\`.
2. Copy `FlightQuoteAssistant.exe` into it.
3. Double-click to run. Windows will create `C:\FlightQuoteAssistant\data\`
   automatically on first launch.
4. Optionally right-click the EXE → **Send to → Desktop (create
   shortcut)** so staff can launch it from the desktop.

### Windows SmartScreen / antivirus warning

Because the EXE isn't code-signed, Windows may show **"Windows protected
your PC"** the first time it's run on a machine. This is expected for an
unsigned, internally-built app — click **More info → Run anyway**. If
your organization has a code-signing certificate, you can sign the EXE
afterward with `signtool sign /f yourcert.pfx /p password
dist\FlightQuoteAssistant.exe` to avoid the warning entirely; this is
optional and not required for the app to work.

### Setting up API keys per install

The SerpAPI and OpenAI keys are stored per-installation (in that PC's
local `data\flight_quote_assistant.db`), not baked into the EXE. Each
staff PC needs its own key entered once via the **Settings** tab, or you
can distribute a `data` folder pre-populated with a shared key already
saved (copy it into place before first run).

### Updating to a new version

PyInstaller EXEs don't auto-update. To roll out a new version:

1. Make your code changes, rebuild with the command in step 8.
2. Send the new `FlightQuoteAssistant.exe` to staff to replace the old
   one (same filename is fine).
3. **Do not delete their `data` folder** — replacing only the `.exe` file
   keeps all saved quotes and settings intact, since they live in a
   separate SQLite file the new EXE will keep reading from.

### Uninstalling

There's no installer/uninstaller — just delete the folder containing
`FlightQuoteAssistant.exe` and its `data` subfolder. Nothing is written
to the Windows registry or `Program Files`.

### Multi-user / shared PC note

If several staff share one PC and should **not** share saved quotes, give
each Windows user account its own copy of the EXE + `data` folder (e.g.
under each user's own Documents folder) rather than one shared install.

## Troubleshooting

- **"No module named customtkinter"** — activate the virtual environment
  and re-run `pip install -r requirements.txt`.
- **App opens but search shows no results** — widen your date range,
  relax filters (allow 1 stop, increase max layover, remove blocked
  airlines), or increase the maximum fare per person. The app will show
  these suggestions automatically when nothing matches.
- **"DOWN date before UP date" error** — the DOWN date range or calculated
  DOWN dates fall before the UP date; adjust the package duration or
  manual DOWN date range.
- **SerpAPI errors ("Live search failed for...")** — the search stops and
  shows exactly what went wrong instead of quietly using mock data. Common
  causes: an invalid/expired API key, quota exceeded, or an airport/city
  code Google Flights doesn't recognize (try the 3-letter IATA code
  directly if a typed city name isn't matching). Fix the cause and search
  again — it will not silently substitute fake fares for a live search.
- **PDF/Excel export fails** — make sure the target folder isn't open in
  another program (e.g. the PDF/Excel file itself already open) and that
  you have write permission to the chosen folder.
- **EXE won't start / blank window** — try running `python main.py` first
  to confirm the app works from source, then rebuild with
  `--collect-all customtkinter`.

## Project structure

```
main.py                       Entry point
config.py                     App constants & default settings
models.py                     Data models (dataclasses)
database.py                   SQLite persistence (settings, cache, saved quotes)
providers/base.py             Abstract FlightProvider interface
providers/mock_provider.py    Offline mock flight data
providers/serpapi_provider.py SerpAPI (Google Flights) live integration
services/search_service.py    Search orchestration + caching
services/ranking_service.py   Hard-reject rules + scoring + best-4 selection
services/date_pair_service.py UP/DOWN valid date pair generation
services/export_service.py    WhatsApp / PDF / Excel export
services/ai_summary_service.py Optional OpenAI customer quote wording
ui/app.py                     Main window, 4 tabs
ui/search_form.py             New Quote form
ui/results_view.py            Results tab (best 4 package cards)
ui/settings_view.py           Settings tab
utils/date_utils.py           Date helpers
utils/airport_utils.py        City/airport code lookup (manual entry always allowed)
```
