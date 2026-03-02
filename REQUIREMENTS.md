# Requirements Specification v3

Back-of-the-Envelope Resource Estimation Calculator

---

## 1. Functional Requirements

### FR-01 Input Parameters

| ID | Parameter | Type | Constraints |
|---|---|---|---|
| FR-01-1 | Daily Active Users (DAU) | Positive integer | Supports K/M/B/T suffix, range 1 to 100T |
| FR-01-2 | Read:Write Ratio | Positive integer | Range 1 to 1000, displayed as N:1 |
| FR-01-3 | Write operations per user per day | Positive float | Range 0.001 to 10,000 |
| FR-01-4 | Data per write request | Positive float + unit | Units: B/KB/MB/GB/TB/PB/EB/ZB/YB |
| FR-01-5 | Data retention | Positive integer | Unit: months, range 1 to 1200 (100 years) |
| FR-01-6 | Precision Mode | Boolean toggle | Default: Off |

### FR-02 Calculation Outputs

| ID | Output | Formula |
|---|---|---|
| FR-02-1 | Write RPS | DAU × writes_per_user / seconds_per_day |
| FR-02-2 | Read RPS | Write RPS × read_write_ratio |
| FR-02-3 | Daily Storage | DAU × writes_per_user × data_per_write_bytes |
| FR-02-4 | Monthly Storage | Daily Storage × 30 |
| FR-02-5 | Total Storage | Daily Storage × retention_months × 30 |

### FR-03 Precision Mode Behavior

| Parameter | Precision Off | Precision On |
|---|---|---|
| seconds_per_day | 100,000 | 86,400 |
| Unit conversion base | 1000 | 1024 |

### FR-04 Real-Time Calculation

Any change to any input field triggers recalculation. All output values must update within 200 ms. No explicit "Calculate" button is required.

### FR-05 DAU Suffix Parsing

| Input | Parsed Value | Display |
|---|---|---|
| 300M | 300,000,000 | "300M" |
| 1.5B | 1,500,000,000 | "1.5B" |
| 500K | 500,000 | "500K" |
| 2T | 2,000,000,000,000 | "2T" |
| 300000000 | 300,000,000 | "300M" |

On blur or Enter, the field re-displays the compact formatted version. Parsing is case-insensitive.

### FR-06 Output Unit Auto-Formatting

Result values are automatically formatted to the most appropriate unit, with 2 decimal places. Example: 25,000,000,000 bytes displays as "25.00 GB" (Precision Off) or "23.28 GiB" (Precision On).

### FR-07 Storage Description Text

Storage results are presented as a natural-language sentence:

```
Storage: {daily} of new storage every day, or around {monthly} per month. And total: {total}.
```

The template is translated per the active language (see FR-11).

### FR-08 Reference Data Tables

Five read-only reference tables are embedded in the interface:

**Images**

| Quality | Size | Example |
|---|---|---|
| Low | 10 KB | Thumbnail, small website images |
| Medium | 100 KB | Website photos |
| High | 2 MB | Phone camera photo |
| Very High | 20 MB | RAW photographer image |

**Videos**

| Quality | Size | Example |
|---|---|---|
| Low | 2 MB/min | 480p video |
| Medium | 20 MB/min | 1080p video |
| High | 80 MB/min | 4K video |

**Audio**

| Quality | Size | Example |
|---|---|---|
| Low | 700 KB | Low quality MP3 |
| High | 3 MB | High quality MP3 |

**Bandwidth**

| Bandwidth | Application |
|---|---|
| 80 Kbps | VoIP calling |
| 150 Kbps | Screen sharing |
| 0.5 Mbps | Live streaming webinars |
| 3 Mbps | 720p video / Zoom meetings |
| 5 Mbps | HD 1080p streaming (YouTube/Netflix) |
| 25 Mbps | 4K Ultra HD video |

**Datastore Latency**

| Storage | Latency | Relative Speed |
|---|---|---|
| Disk | 3 ms | baseline |
| SSD | 0.2 ms | 15× faster |
| Memory | 0.01 ms | 300× faster |

### FR-09 Copy Shareable Link

Clicking the button encodes all current input parameters as a URL query string and writes it to the system clipboard. Passing that string back via the `--params` CLI argument restores all field values.

Format:

```
?dau=300M&rw_ratio=10&writes=1&data=50&data_unit=KB&retention=120&precision=0
```

### FR-10 Design Strategy Hints

A contextual hint is displayed based on the Read:Write Ratio:

- Ratio ≥ 10: *"High read ratio: consider caching and read replicas."*
- Ratio = 1: *"High write ratio: consider write-optimized stores and eventual consistency."*
- Otherwise: no hint shown

### FR-11 Language Switching

| ID | Description |
|---|---|
| FR-11-1 | Supports English (en) and Simplified Chinese (zh) |
| FR-11-2 | Language toggle in the top-right corner (EN / 中文 buttons) |
| FR-11-3 | All UI text updates immediately on switch — no restart needed |
| FR-11-4 | Switching language does not affect any input values or calculation results |
| FR-11-5 | Default language on startup: English |

### FR-12 Translatable Text Scope

All of the following must support both languages:

- Application title, panel titles, all input field labels
- Unit annotations (months, seconds/day, etc.)
- Precision Mode label
- Storage description template (FR-07)
- Strategy hint text (FR-10)
- Reference table titles, column headers, and row content descriptions
- Button labels, Toast notifications, error messages

**Not translated:** numeric values, unit abbreviations (KB, MB, RPS), URL query string keys.

### FR-13 Translation Data Structure

All translations are defined in a single top-level dictionary. Adding a new language requires only adding a new key to this dictionary — no UI code changes.

```python
TRANSLATIONS = {
    "en": {
        "app_title": "Back-of-the-Envelope Resource Estimator",
        "result_storage_template": (
            "Storage: {daily} of new storage every day, "
            "or around {monthly} per month. And total: {total}."
        ),
        ...
    },
    "zh": {
        "app_title": "系统资源粗估计算器",
        "result_storage_template": (
            "存储：每天新增 {daily}，每月约 {monthly}，总计 {total}。"
        ),
        ...
    }
}
```

---

## 2. Non-Functional Requirements

### NFR-01 Performance

- Application startup time: < 2 seconds on a standard laptop
- Input-to-result refresh latency: < 200 ms

### NFR-02 Compatibility

- Python 3.10 and above
- Standard library only — zero third-party dependencies
- Single-file execution
- Supported platforms: Windows 10+, macOS 12+, Ubuntu 22.04+

### NFR-03 Usability

- Minimum window size: 900 × 600 px, freely resizable with adaptive layout
- Reference tables are scrollable and do not obstruct inputs or results
- Invalid input fields show a red border with a tooltip; no crash, no clearing of other fields

### NFR-04 Maintainability

- Calculation logic, translation management, and UI code are separated into distinct classes
- Reference data and translation strings are defined as top-level constants — no magic values in UI code

### NFR-05 Visual Style

- Light or neutral-dark theme
- Result key figures highlighted in blue or orange
- System default monospace font for numeric display — no external font files required

### NFR-06 i18n Extensibility

Translation dictionaries are fully decoupled from UI logic. Adding a third language (e.g., Traditional Chinese, Japanese) requires only a new entry in `TRANSLATIONS` — no UI logic changes.

### NFR-07 CJK Font Compatibility

When Chinese is active, the application detects the best available CJK font in this order:

- Windows: Microsoft YaHei
- macOS: PingFang SC
- Linux: Noto Sans CJK SC

Falls back to the tkinter system default. Chinese characters must never display as boxes or garbled text.

---

## 3. Acceptance Criteria

### AC-01 Calculation Correctness

**Given** DAU=500,000 / ratio=5 / writes=1 / data=50 KB / retention=120 months / Precision Off

**Then:**
- Write RPS = 5.00
- Read RPS = 25.00
- Daily Storage = 25 GB
- Monthly Storage = 750 GB
- Total Storage = 90 TB

### AC-02 Precision Mode Toggle

**Given** any valid parameter set, user toggles Precision Mode

**Then** all results update within 200 ms; numeric values change; unit labels reflect the active base (GB vs GiB)

### AC-03 DAU Suffix Parsing

**Given** user types "300M" and presses Enter

**Then** the internal value is 300,000,000; the field re-displays "300M"; results update immediately

### AC-04 Invalid Input Handling

**Given** user types "abc" or "-1" in the DAU field

**Then** that field shows a red border; the results area shows "Invalid input"; all other fields and results are unaffected

### AC-05 Read:Write Ratio = 1

**Given** ratio is set to 1

**Then** Read RPS equals Write RPS exactly; no division-by-zero error; no strategy hint is displayed

### AC-06 Shareable Link Round-Trip

**Given** user configures parameters and clicks "Copy Shareable Link"

**Then** the clipboard contains a valid query string; launching the app with that string via `--params` restores all fields to those exact values

### AC-07 Reference Table Completeness

**Given** the application has finished launching

**Then** all five reference tables (Images, Videos, Audio, Bandwidth, Datastore Latency) are visible or reachable by scrolling, with data matching this specification exactly

### AC-08 Window Resize

**Given** user resizes the window anywhere between 900×600 and 1600×1000

**Then** all controls remain visible, operable, and non-overlapping

### AC-09 Language Switch Preserves Values

**Given** user has entered a parameter set in English and switches to Chinese

**Then** all numeric input values and calculated results are identical before and after the switch; only display text changes

### AC-10 Description Template in Both Languages

**Given** results are Daily=78 GB, Monthly=2 TB, Total=142 TB

**Then:**
- English: `Storage: 78.00 GB of new storage every day, or around 2.00 TB per month. And total: 142.00 TB.`
- Chinese: `存储：每天新增 78.00 GB，每月约 2.00 TB，总计 142.00 TB。`

### AC-11 Reference Tables in Both Languages

**Given** user switches to Chinese

**Then** all table titles, column headers, and row description text display in Chinese

### AC-12 Error Messages in Both Languages

**Given** an invalid input exists and the user switches language

**Then** the error message immediately reflects the newly active language ("Invalid input" / "输入无效")

---

## 4. Invariants

These constraints must hold at all times, under any input or user action.

### INV-01 Non-Negative Outputs

```
Write RPS >= 0
Read RPS >= 0
Daily Storage >= 0
Monthly Storage >= 0
Total Storage >= 0
```

### INV-02 Read RPS >= Write RPS

```
read_write_ratio >= 1 (minimum allowed value)
Read RPS = Write RPS × read_write_ratio
Therefore Read RPS >= Write RPS always
```

### INV-03 Storage Monotonicity

```
retention_months >= 1
Monthly Storage = Daily Storage × 30
Total Storage = Daily Storage × retention_months × 30
Therefore Total Storage >= Monthly Storage >= Daily Storage >= 0
```

### INV-04 Precision Mode Does Not Modify Inputs

Toggling Precision Mode changes only `seconds_per_day` and `unit_base` used in calculation. It never modifies any user-entered field value or its internal representation.

### INV-05 Reference Data Is Immutable

The five reference tables are constants. No user action can alter their content during a session.

### INV-06 Unit Base Consistency

Within a single calculation pass, the same base (1000 or 1024) must be used consistently across input parsing, calculation, and output formatting. Mixing bases within one pass is a violation.

### INV-07 DAU Is Always a Positive Integer

After suffix parsing, DAU is stored as a Python `int` (never `float`). The value is always ≥ 1 when valid.

### INV-08 Invalid Input Does Not Propagate

When a field contains an invalid value, the previous valid value continues to be used in calculation (or the results area shows an error state). The invalid value is never passed into the calculation pipeline.

### INV-09 Language Switch Does Not Trigger Recalculation

```
Write RPS (before switch) == Write RPS (after switch)
Read RPS (before switch) == Read RPS (after switch)
All storage values (before switch) == All storage values (after switch)
```

A language switch only updates display text; it never calls `Calculator.compute()`.

### INV-10 Translation Key Completeness

For every translation key `k`, `k` must exist in both `TRANSLATIONS["en"]` and `TRANSLATIONS["zh"]`. A missing key falls back to the English value and prints a `WARNING` to stdout — it never raises a `KeyError` at runtime.
