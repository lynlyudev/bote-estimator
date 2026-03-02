# Design Specification v1

Back-of-the-Envelope Resource Estimation Calculator

---

## 1. Architecture

### 1.1 Three-Layer Separation

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Layer                             │
│   AppWindow / InputPanel / ResultPanel / ReferencePanel     │
│   Language toggle / Error display / Toast notifications     │
│   Responsibilities: read inputs, call Calculator,           │
│   render results, trigger I18n text refresh                 │
└────────────────────────┬────────────────────────────────────┘
                         │ calls
┌────────────────────────▼────────────────────────────────────┐
│                    Domain Layer                             │
│   Calculator    — pure computation, no side effects         │
│   InputParser   — DAU suffix parsing, unit conversion       │
│   OutputFormatter — numeric-to-string formatting            │
│   I18n          — translation key lookup, language state    │
└────────────────────────┬────────────────────────────────────┘
                         │ reads
┌────────────────────────▼────────────────────────────────────┐
│                     Data Layer                              │
│   TRANSLATIONS   — bilingual translation constant dict      │
│   REFERENCE_DATA — five reference table constants           │
│   UNIT_SCALES    — unit conversion table constants          │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Event-Driven Calculation Flow

```
User modifies any input field
        │
        ▼
InputPanel._on_change()
        │
        ├─► InputParser.parse_dau(raw_str)        → int | None
        ├─► InputParser.parse_data_size(v, u, b)  → int | None
        └─► All fields valid?
                │ Yes                    │ No
                ▼                        ▼
        Calculator.compute(params)   Mark field INVALID
                │                    ResultPanel.render_error()
                ▼                    (INV-08: no propagation)
        EstimationResult (frozen dataclass)
                │
                ▼
        OutputFormatter.format(result)
                │
                ▼
        ResultPanel.render(formatted_result)
```

### 1.3 Language Switch Flow

```
User clicks language toggle
        │
        ▼
I18n.set_language(lang)
        │
        ▼
AppWindow._refresh_texts()
        │   Iterates all registered (widget, translation_key) bindings
        ▼
widget.config(text=i18n.t(key))   for each binding
        │
        ▼
ResultPanel._rerender_description()
        │   Re-formats existing result with new language template
        ▼
(Calculator.compute() is NOT called — INV-09)
```

---

## 2. Technology Choices

### 2.1 GUI Framework: tkinter + ttk

| Dimension | tkinter + ttk | PyQt6 |
|---|---|---|
| Dependencies | Python standard library, zero install | pip install, ~60 MB |
| Single-file | Yes | No |
| Cross-platform | Windows / macOS / Linux | Windows / macOS / Linux |
| Modern widgets | ttk provides adequate styling | Richer |
| Suitable for this project | Yes | Overkill |

**Decision:** tkinter + ttk. Custom colors via `ttk.Style`. Satisfies NFR-02 (zero dependencies).

### 2.2 Numeric Types

- DAU: Python `int` — arbitrary precision, no float rounding (INV-07)
- RPS: `float` — displayed to 2 decimal places
- Storage (bytes): `int` — avoids float accumulation error; converted to float only at formatting time
- No numpy, decimal, or math imports needed

### 2.3 Clipboard

`tk.Tk.clipboard_clear()` and `clipboard_append()` from the standard tkinter API. No third-party library.

### 2.4 CJK Font Detection

`tkinter.font.families()` returns all system-available font families. Fonts are tested in the priority order defined in NFR-07; the first match is used, falling back to the tkinter default.

---

## 3. Module Breakdown

All code resides in the single file `estimator.py`:

```
estimator.py
│
├── [Constants — Data Layer]
│   ├── UNIT_SCALES          Unit name → multiplier, for both bases
│   ├── REFERENCE_DATA       Five reference tables (translation keys + fixed strings)
│   └── TRANSLATIONS         Full bilingual translation dictionary
│
├── [Domain Layer]
│   ├── class InputParser    parse_dau(), parse_data_size(), format_dau()
│   ├── class Calculator     compute(params) → EstimationResult
│   ├── class OutputFormatter format_bytes(), format_rps(), format_description()
│   └── class I18n           set_language(), t(), current_lang
│
├── [Data Models]
│   ├── dataclass EstimationParams
│   ├── dataclass EstimationResult   (frozen, with __post_init__ invariant checks)
│   └── dataclass FormattedResult
│
├── [UI Layer]
│   ├── class AppWindow      Main window; owns all panels; handles layout and lang toggle
│   ├── class InputPanel     Left column: all input controls and _on_change dispatch
│   ├── class ResultPanel    Right column upper: RPS display, storage text, strategy hint
│   └── class ReferencePanel Right column lower: scrollable five-table reference area
│
└── if __name__ == "__main__":
        argparse setup (--lang, --params)
        AppWindow instantiation and mainloop
```

### 3.1 Module Responsibility Boundaries

| Module | May Do | Must Not Do |
|---|---|---|
| Calculator | Accept parsed numeric inputs, return result dataclass | Access UI widgets, parse strings, read translations |
| InputParser | Convert strings to validated numbers | Modify UI state, perform calculations |
| OutputFormatter | Format numbers to display strings | Perform calculations, read translation dict |
| I18n | Translate keys, track active language | Modify any UI widget |
| UI classes | Read inputs, call domain classes, render | Contain business logic or calculation formulas |

---

## 4. Data Models

### 4.1 Input Parameters

```python
@dataclass
class EstimationParams:
    dau: int                    # Daily active users, positive integer
    read_write_ratio: int       # Reads per write, minimum 1
    writes_per_user: float      # Write operations per user per day
    data_per_write_bytes: int   # Bytes per write request
    retention_months: int       # Data retention period in months
    precision_mode: bool        # False = rough estimate, True = precise

    @property
    def seconds_per_day(self) -> int:
        return 86_400 if self.precision_mode else 100_000

    @property
    def unit_base(self) -> int:
        return 1024 if self.precision_mode else 1000
```

### 4.2 Calculation Result

```python
@dataclass(frozen=True)
class EstimationResult:
    write_rps: float
    read_rps: float
    daily_storage_bytes: int
    monthly_storage_bytes: int
    total_storage_bytes: int
    unit_base: int              # Carried through for consistent formatting

    def __post_init__(self):
        # Invariant assertions (INV-01, INV-02, INV-03)
        assert self.write_rps >= 0
        assert self.read_rps >= self.write_rps
        assert self.daily_storage_bytes >= 0
        assert self.monthly_storage_bytes >= self.daily_storage_bytes
        assert self.total_storage_bytes >= self.monthly_storage_bytes
```

### 4.3 Formatted Output

```python
@dataclass
class FormattedResult:
    write_rps_str: str       # e.g. "5.00"
    read_rps_str: str        # e.g. "25.00"
    daily_str: str           # e.g. "25.00 GB"
    monthly_str: str         # e.g. "750.00 GB"
    total_str: str           # e.g. "90.00 TB"
    description: str         # Full natural-language sentence (translated)
    strategy_hint: str       # Strategy hint text, or "" if none applies
```

### 4.4 Unit Scales

```python
# Built at module level for both bases
def _build_unit_scales(base: int) -> list[tuple[str, int]]:
    suffixes = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    return [(s, base ** i) for i, s in enumerate(suffixes)]

UNIT_SCALES_1000 = _build_unit_scales(1000)
UNIT_SCALES_1024 = _build_unit_scales(1024)
```

### 4.5 Reference Data Structure

```python
REFERENCE_DATA = {
    "images": [
        {"quality_key": "img_low",    "size": "10 KB",     "example_key": "img_low_ex"},
        {"quality_key": "img_medium", "size": "100 KB",    "example_key": "img_medium_ex"},
        {"quality_key": "img_high",   "size": "2 MB",      "example_key": "img_high_ex"},
        {"quality_key": "img_vhigh",  "size": "20 MB",     "example_key": "img_vhigh_ex"},
    ],
    "videos": [
        {"quality_key": "vid_low",    "size": "2 MB/min",  "example_key": "vid_low_ex"},
        {"quality_key": "vid_medium", "size": "20 MB/min", "example_key": "vid_medium_ex"},
        {"quality_key": "vid_high",   "size": "80 MB/min", "example_key": "vid_high_ex"},
    ],
    "audio": [
        {"quality_key": "aud_low",    "size": "700 KB",    "example_key": "aud_low_ex"},
        {"quality_key": "aud_high",   "size": "3 MB",      "example_key": "aud_high_ex"},
    ],
    "bandwidth": [
        {"bw": "80 Kbps",   "app_key": "bw_voip"},
        {"bw": "150 Kbps",  "app_key": "bw_screen"},
        {"bw": "0.5 Mbps",  "app_key": "bw_webinar"},
        {"bw": "3 Mbps",    "app_key": "bw_720p"},
        {"bw": "5 Mbps",    "app_key": "bw_1080p"},
        {"bw": "25 Mbps",   "app_key": "bw_4k"},
    ],
    "latency": [
        {"storage_key": "lat_disk",   "latency": "3 ms",    "note_key": "lat_disk_note"},
        {"storage_key": "lat_ssd",    "latency": "0.2 ms",  "note_key": "lat_ssd_note"},
        {"storage_key": "lat_memory", "latency": "0.01 ms", "note_key": "lat_mem_note"},
    ],
}
```

`size`, `bw`, and `latency` fields are fixed strings that need no translation. All `*_key` fields are resolved at render time via `i18n.t()`.

### 4.6 I18n Class Interface

```python
class I18n:
    def __init__(self, default_lang: str = "en") -> None: ...

    def set_language(self, lang: str) -> None:
        # Sets active language; raises ValueError for unknown lang
        ...

    def t(self, key: str) -> str:
        # Returns translated string for key in active language.
        # On missing key: returns TRANSLATIONS["en"][key],
        # prints WARNING to stdout. Never raises KeyError. (INV-10)
        ...

    @property
    def current_lang(self) -> str: ...
```

---

## 5. Boundary and Exception Strategy

### 5.1 Input Boundaries

| Field | Min | Max | On Violation |
|---|---|---|---|
| DAU | 1 | 100,000,000,000,000 (100T) | Field turns red, results show error state |
| Read:Write Ratio | 1 | 1,000 | Same |
| Writes/User/Day | 0.001 | 10,000 | Same |
| Data per Write | 0.001 (any unit) | Python int ceiling | Same |
| Retention (months) | 1 | 1,200 | Same |

### 5.2 Exception Classification

| Exception | Source | Handling |
|---|---|---|
| `ValueError` (bad string) | `InputParser` | Caught; returns `None`; UI marks field red |
| `OverflowError` (value too large) | Unit conversion | Caught; treated as above-max; UI shows "Value too large" |
| `KeyError` (missing translation) | `I18n.t()` | Caught; returns English fallback; prints WARNING (INV-10) |
| `AssertionError` (invariant breach) | `EstimationResult.__post_init__` | Not caught — propagates as a programming error, visible in dev |
| `ZeroDivisionError` | `Calculator` | Theoretically unreachable (`seconds_per_day` is always > 0); guarded by `assert seconds_per_day > 0` |

### 5.3 Invalid Input Non-Propagation (INV-08)

```
InputPanel._on_change()
        │
        ├─► Any field parse result is None?
        │       │ Yes: mark field.state = INVALID
        │       │      ResultPanel.render_error()
        │       │      Do not call Calculator
        │       │      Other fields retain last valid displayed value
        │       │
        │       └─► No: continue to next check
        │
        └─► All fields valid?
                │ Yes: Calculator.compute(params)  →  ResultPanel.render(result)
                └─► No: ResultPanel.render_error()
```

### 5.4 Extreme Value Handling

- **Very small:** DAU=1, writes=0.001, data=1B → results near zero; formatter displays "0.00 B/day" without error
- **Very large:** DAU=100T, writes=10,000, data=1 TB → daily storage ~10²⁷ bytes (~1 YB range); Python `int` handles this without overflow; `OutputFormatter` supports up to YB
- **Long retention:** 1,200 months = 100 years; total = daily × 36,000; well within Python int range

### 5.5 Shareable Link Encoding and Decoding

- **Encoding:** All parameters serialized as ASCII query string; no spaces or special characters
- **Decoding:** Unknown or malformed keys are silently ignored; missing keys use defaults; never crashes on bad input
- **Forward compatibility:** Future parameter additions are backward-compatible because the decoder skips unknown keys
