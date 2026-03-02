# Task Breakdown v1

Back-of-the-Envelope Resource Estimation Calculator

Tasks are ordered by dependency. Each phase assumes the previous phase is complete.

---

## 1. Implementation Steps

### Phase 1: Foundation

**T-01 Project Entry Point and Main Window Skeleton**

- Create `estimator.py` as a single-file project
- Implement `main()`: initialize `tk.Tk()`, set window title, minimum size (900×600)
- Implement `argparse` setup for `--lang` and `--params` CLI arguments
- Wire `AppWindow` stub into `main()` and call `mainloop()`
- Acceptance: running the file produces an empty resizable window with a correct title

**T-02 Constant Layer**

- Define `UNIT_SCALES_1000` and `UNIT_SCALES_1024` (B through YB)
- Define `REFERENCE_DATA` for all five tables (translation key fields + fixed size/latency strings)
- Define `TRANSLATIONS` for both `"en"` and `"zh"`, covering every key in `TRANSLATION_KEYS`
- Add a module-level assertion: `set(TRANSLATIONS["en"].keys()) == set(TRANSLATIONS["zh"].keys())` (INV-10)
- Acceptance: `python -c "import estimator"` exits with no errors; key-set assertion passes

**T-03 I18n Module**

- Implement `class I18n` with `set_language()`, `t()`, `current_lang`
- `t()` falls back to English and prints `WARNING: missing translation key '{key}' for lang '{lang}'` on any missing key (INV-10)
- Acceptance: T-TEST-01 unit tests pass

---

### Phase 2: Domain Layer

**T-04 InputParser Module**

- Implement `parse_dau(raw: str) -> int | None`
  - Case-insensitive suffix support: K, M, B, T
  - Accepts plain integers and decimal-with-suffix (e.g., "1.5B")
  - Range validation: 1 to 100,000,000,000,000; returns `None` outside range
- Implement `parse_data_size(value: float, unit: str, base: int) -> int | None`
  - Converts value + unit to bytes using the given base
  - Returns `None` on zero, negative, or overflow
- Implement `format_dau(n: int) -> str`
  - Formats an integer back to compact form: 300,000,000 → "300M"
  - Uses the largest applicable suffix with up to 2 decimal places
- Acceptance: T-TEST-02 unit tests pass

**T-05 Calculator Module**

- Define `EstimationParams` dataclass with `seconds_per_day` and `unit_base` properties
- Define `EstimationResult` frozen dataclass with `__post_init__` invariant assertions (INV-01/02/03)
- Implement `Calculator.compute(params: EstimationParams) -> EstimationResult`
  - Applies formulas from FR-02 exactly
- Acceptance: T-TEST-03 unit tests pass, including the AC-01 reference example

**T-06 OutputFormatter Module**

- Implement `format_bytes(n: int, base: int) -> str`
  - Selects the largest unit where the value is ≥ 1; rounds to 2 decimal places
  - Handles 0 as "0.00 B"
  - Supports up to YB for extreme inputs
- Implement `format_rps(rps: float) -> str`
  - Standard 2-decimal formatting; values below 0.01 display as "< 0.01"
- Implement `format_description(result: EstimationResult, template: str) -> str`
  - Injects `{daily}`, `{monthly}`, `{total}` into the translated template string
- Acceptance: T-TEST-04 unit tests pass

---

### Phase 3: UI Layer

**T-07 CJK Font Detection Utility**

- Implement `detect_cjk_font() -> str`
  - Queries `tkinter.font.families()`
  - Tries fonts in order: Microsoft YaHei → PingFang SC → Noto Sans CJK SC
  - Returns the first available match; falls back to `""` (tkinter default)
- Acceptance: manual test on Windows, macOS, and Ubuntu confirms Chinese characters render without boxes

**T-08 InputPanel**

- Implement the left-column panel with controls:
  - DAU text entry: blur/Enter triggers `format_dau` re-display (FR-05)
  - Read:Write Ratio integer entry
  - Writes/User/Day float entry
  - Data per Write float entry + unit dropdown (B/KB/MB/GB/TB/PB/EB/ZB/YB)
  - Retention integer entry (months)
  - Precision Mode `ttk.Checkbutton` toggle
- All controls bind to `_on_change` for real-time dispatch (FR-04)
- Invalid fields get a red border; valid fields restore normal border (AC-04)
- Implement `get_params() -> EstimationParams | None`: returns `None` if any field is invalid
- Acceptance: manual testing confirms all controls are operable and invalid input turns the field red

**T-09 ResultPanel**

- Implement the right-column upper panel:
  - Write RPS — large bold label with colored highlight (NFR-05)
  - Read RPS — same styling
  - Storage description paragraph (FR-07 template)
  - Strategy hint area — visible only when ratio conditions are met (FR-10); hidden otherwise
- Implement `render(result: FormattedResult)` to update all labels
- Implement `render_error()` to show "Invalid input" / "输入无效" in the result area
- Implement `_rerender_description()` to re-format the current result with the active language template
- Acceptance: manual testing confirms results display correctly and strategy hint appears/disappears correctly

**T-10 ReferencePanel**

- Implement the right-column lower panel with a vertical scrollable container
- Render all five tables using `ttk.Treeview` or a grid of `ttk.Label` widgets
- All column headers and row content resolved via `i18n.t()` at render time (FR-08)
- Implement `refresh_texts()` to re-render headers and content when language changes (FR-11-3)
- Acceptance: manual testing confirms all five tables are complete, scrollable, and switch language correctly

**T-11 Language Toggle and Text Refresh**

- Add EN / 中文 button pair to the top-right area of `AppWindow`
- Implement `AppWindow._refresh_texts()`:
  - Iterates a registered list of `(widget, translation_key)` pairs
  - Calls `widget.config(text=i18n.t(key))` for each
- Wire `ResultPanel._rerender_description()` into the refresh sequence
- Wire `ReferencePanel.refresh_texts()` into the refresh sequence
- Verify Calculator is never called during this sequence (INV-09)
- Acceptance: AC-09 / AC-10 / AC-11 / AC-12 all pass on manual verification

**T-12 Copy Shareable Link**

- Implement parameter serialization: all `EstimationParams` fields → query string
- Implement parameter deserialization from query string → pre-fill all input fields on startup
- Button click: serialize → write to clipboard → show Toast label for 2 seconds then hide
- Toast text is translated per active language ("Copied!" / "已复制！")
- Acceptance: AC-06 passes; copy, restart with `--params`, all fields restore correctly

**T-13 Layout Integration and Styling**

- Compose `InputPanel` (left column) and `ResultPanel` + `ReferencePanel` (right column) into a two-column `grid` layout
- Use `columnconfigure(weight=1)` and `rowconfigure(weight=1)` for proportional scaling
- Apply `ttk.Style` for color theme: result figures in blue (`#2563EB`) or orange (`#EA580C`), neutral backgrounds
- Minimum window size enforced via `wm_minsize(900, 600)`
- Acceptance: AC-08 manual resize test passes at 900×600 and 1600×1000

---

### Phase 4: Integration and Polish

**T-14 End-to-End Integration**

- Run all AC-01 through AC-12 acceptance criteria manually
- Fix any interaction bugs exposed during integration (event ordering, widget state conflicts, etc.)
- Verify startup time is under 2 seconds on a standard laptop (NFR-01)

**T-15 CLI Argument Wiring**

- `--lang en|zh` sets the startup language before the window opens
- `--params "?dau=..."` pre-fills all fields from the query string; unknown keys are silently ignored
- Bad `--params` input falls back to defaults without crashing
- Acceptance: `python estimator.py --lang zh --params "?dau=1B&rw_ratio=5&writes=2&data=100&data_unit=KB&retention=60&precision=1"` opens correctly in Chinese with all fields populated

---

## 2. Test Tasks

### Unit Tests (automated, stdlib `unittest`)

**T-TEST-01 I18n**

```
- t("app_title") returns correct value in both "en" and "zh"
- set_language("zh") → current_lang == "zh"
- t("nonexistent_key") returns English fallback without raising an exception
- set(TRANSLATIONS["en"].keys()) == set(TRANSLATIONS["zh"].keys())  [INV-10]
- set_language("fr") raises ValueError
```

**T-TEST-02 InputParser**

```
- parse_dau("300M")     == 300_000_000
- parse_dau("1.5B")     == 1_500_000_000
- parse_dau("500k")     == 500_000          (case-insensitive)
- parse_dau("2T")       == 2_000_000_000_000
- parse_dau("100T")     == 100_000_000_000_000   (upper boundary)
- parse_dau("101T")     is None              (above upper boundary)
- parse_dau("abc")      is None
- parse_dau("-1")       is None
- parse_dau("0")        is None
- parse_dau("500000")   == 500_000          (plain integer)
- parse_data_size(50, "KB", 1000) == 50_000
- parse_data_size(50, "KB", 1024) == 51_200
- parse_data_size(0,  "MB", 1000) is None   (zero value)
- parse_data_size(-1, "MB", 1000) is None   (negative value)
- format_dau(300_000_000)   == "300M"
- format_dau(500_000)       == "500K"
- format_dau(1_500_000_000) == "1.5B"
- format_dau(1_000)         == "1K"
```

**T-TEST-03 Calculator**

```
Reference example (AC-01, Precision Off):
  params: dau=500_000, ratio=5, writes=1.0, data=50_000 bytes, retention=120, precision=False
  result.write_rps          == 5.0
  result.read_rps           == 25.0
  result.daily_storage_bytes  == 25_000_000_000
  result.monthly_storage_bytes == 750_000_000_000
  result.total_storage_bytes   == 90_000_000_000_000

Precision On (same inputs, different seconds_per_day):
  result.write_rps != 5.0   (86400 denominator gives ~5.787)

Invariant checks:
  For any valid params: read_rps >= write_rps               [INV-02]
  For any valid params: total >= monthly >= daily >= 0      [INV-01, INV-03]

Ratio = 1:
  read_rps == write_rps
```

**T-TEST-04 OutputFormatter**

```
- format_bytes(25_000_000_000, 1000)  == "25.00 GB"
- format_bytes(25_000_000_000, 1024)  starts with "23.28"   (GiB range)
- format_bytes(0, 1000)               == "0.00 B"
- format_bytes(10**27, 1000)          contains "YB"
- format_rps(25.0)                    == "25.00"
- format_rps(0.001)                   == "< 0.01"
- format_rps(0.0)                     == "0.00"
- format_description with template "{daily} / {monthly} / {total}"
  produces a string containing all three formatted values
```

### Integration Tests (manual verification checklist)

**T-TEST-05 Full Acceptance Criteria Run**

| Case | Action | Expected |
|---|---|---|
| AC-01 | Enter reference example values, Precision Off | Write RPS=5.00, Read RPS=25.00, Daily=25 GB |
| AC-02 | Toggle Precision Mode | Values change within 200 ms |
| AC-03 | Type "300M", press Enter | Field shows "300M", results update |
| AC-04 | Type "abc" in DAU | Red border on field, "Invalid input" in results |
| AC-05 | Set ratio to 1 | Read RPS == Write RPS, no hint shown, no crash |
| AC-06 | Copy link, relaunch with `--params` | All fields restore |
| AC-07 | Launch app, inspect reference panel | All five tables present with correct data |
| AC-08 | Resize to 900×600 then 1600×1000 | No overlap, no clipping |
| AC-09 | Fill fields in English, switch to Chinese | Values unchanged, text in Chinese |
| AC-10 | Verify storage description text format | Correct template in both languages |
| AC-11 | Switch to Chinese, inspect reference tables | Headers and content in Chinese |
| AC-12 | Trigger invalid input, switch language | Error message language updates |

**T-TEST-06 Cross-Platform Smoke Test**

| Platform | Checks |
|---|---|
| Windows 10+ | CJK font renders (Microsoft YaHei), window resizes, clipboard works |
| macOS 12+ | CJK font renders (PingFang SC), Retina display acceptable |
| Ubuntu 22.04 | CJK font renders (Noto Sans CJK SC), tkinter available |

---

## 3. Optional Enhancements

Listed in priority order. None of these are required for the core feature set.

**OPT-01 Dark Theme Support**

- Add a Light / Dark toggle in the settings area
- Implement via `ttk.Style` — swap background, foreground, and highlight colors
- Language and theme toggles are independent

**OPT-02 Scenario Presets**

- Built-in preset configurations for common scenarios: "Social Media", "Video Streaming", "Chat App"
- Selecting a preset fills all input fields with typical values for that scenario
- Preset names are bilingual (follow FR-12 translation scope)

**OPT-03 Storage Growth Chart**

- Draw a simple bar or line chart in the result area using `tkinter.Canvas` (no matplotlib)
- X-axis: time in months up to the retention period; Y-axis: cumulative storage
- Chart updates in real time with input changes

**OPT-04 Export to Text Report**

- "Export Report" button opens a file save dialog
- Generates a Markdown or plain-text summary of all inputs and results
- Report language follows the active UI language

**OPT-05 Keyboard Shortcuts**

- `Ctrl+L` (or `Cmd+L` on macOS): toggle language
- `Ctrl+Shift+C`: copy shareable link (regardless of focus)
- `Tab` order follows a logical top-to-bottom, left-to-right sequence through input fields

**OPT-06 Window State Persistence**

- On exit, write window position, size, and language preference to `~/.bote_estimator.json`
- On next launch, restore that state before displaying the window

**OPT-07 Concurrent Connections Estimator**

- Add an optional "Concurrent Connections" section for WebSocket-heavy use cases (e.g., chat services)
- Inputs: average session duration (minutes), DAU
- Output: estimated peak concurrent connections
- Accompanied by a strategy hint for connection pooling and load balancing
