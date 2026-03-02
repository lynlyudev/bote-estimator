"""
Back-of-the-Envelope Resource Estimator
========================================
Single-file desktop application (Python 3.10+, tkinter only).

Usage:
    python estimator.py
    python estimator.py --lang zh
    python estimator.py --params "?dau=300M&rw_ratio=10&writes=1&data=50&data_unit=KB&retention=120&precision=0"
"""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass, field
from tkinter import ttk
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

# ---------------------------------------------------------------------------
# Data Layer — Constants
# ---------------------------------------------------------------------------

# --- Unit scales ------------------------------------------------------------

def _build_scales(base: int) -> list[tuple[str, int]]:
    suffixes = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    return [(s, base ** i) for i, s in enumerate(suffixes)]

UNIT_SCALES_1000 = _build_scales(1000)
UNIT_SCALES_1024 = _build_scales(1024)

DATA_UNITS = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]

# --- Reference data ---------------------------------------------------------

REFERENCE_DATA: dict[str, list[dict]] = {
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

# --- Translations ------------------------------------------------------------

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # App chrome
        "app_title":          "Back-of-the-Envelope Resource Estimator",
        "input_title":        "Input Parameters",
        "result_title":       "Estimation Results",
        "ref_title":          "Reference Tables",
        # Input labels
        "dau_label":          "Daily Active Users (DAU)",
        "dau_hint":           "e.g. 300M, 1.5B, 500K",
        "rw_label":           "Read : Write Ratio",
        "rw_hint":            "e.g. 10  means 10 : 1",
        "writes_label":       "Writes per User per Day",
        "data_label":         "Data per Write Request",
        "retention_label":    "Data Retention (months)",
        "precision_label":    "Precision Mode",
        "precision_hint":     "Off: 100,000 s/day, 1000-byte units",
        "precision_hint_on":  "On: 86,400 s/day, 1024-byte units",
        # Result labels
        "write_rps_label":    "Write RPS",
        "read_rps_label":     "Read RPS",
        "storage_label":      "Storage",
        "result_storage_tpl": (
            "Storage: {daily} of new storage every day, "
            "or around {monthly} per month. And total: {total}."
        ),
        # Strategy hints
        "hint_high_read":  "High read ratio: consider caching and read replicas.",
        "hint_high_write": "High write ratio: consider write-optimized stores and eventual consistency.",
        # Buttons and actions
        "copy_btn":      "Copy Shareable Link",
        "copied_toast":  "Copied!",
        "invalid_input": "Invalid input — please check highlighted fields.",
        "too_large":     "Value too large.",
        # Reference table section titles
        "ref_images":    "Images",
        "ref_videos":    "Videos",
        "ref_audio":     "Audio",
        "ref_bandwidth": "Bandwidth",
        "ref_latency":   "Datastore Latency",
        # Column headers
        "col_quality":   "Quality",
        "col_size":      "Size",
        "col_example":   "Example",
        "col_bandwidth": "Bandwidth",
        "col_app":       "Application",
        "col_storage":   "Storage",
        "col_latency":   "Latency",
        "col_note":      "Speed",
        # Image quality labels
        "img_low":       "Low",
        "img_medium":    "Medium",
        "img_high":      "High",
        "img_vhigh":     "Very High",
        # Image examples
        "img_low_ex":    "Thumbnail, small website images",
        "img_medium_ex": "Website photos",
        "img_high_ex":   "Phone camera photo",
        "img_vhigh_ex":  "RAW photographer image",
        # Video quality labels
        "vid_low":       "Low",
        "vid_medium":    "Medium",
        "vid_high":      "High",
        # Video examples
        "vid_low_ex":    "480p video",
        "vid_medium_ex": "1080p video",
        "vid_high_ex":   "4K video",
        # Audio quality labels
        "aud_low":       "Low",
        "aud_high":      "High",
        # Audio examples
        "aud_low_ex":    "Low quality MP3",
        "aud_high_ex":   "High quality MP3",
        # Bandwidth app names
        "bw_voip":    "VoIP calling",
        "bw_screen":  "Screen sharing",
        "bw_webinar": "Live streaming webinars",
        "bw_720p":    "720p video / Zoom meetings",
        "bw_1080p":   "HD 1080p streaming (YouTube / Netflix)",
        "bw_4k":      "4K Ultra HD video",
        # Latency storage labels
        "lat_disk":   "Disk",
        "lat_ssd":    "SSD",
        "lat_memory": "Memory",
        # Latency notes
        "lat_disk_note": "baseline",
        "lat_ssd_note":  "15× faster",
        "lat_mem_note":  "300× faster",
    },
    "zh": {
        # App chrome
        "app_title":          "系统资源粗估计算器",
        "input_title":        "输入参数",
        "result_title":       "估算结果",
        "ref_title":          "参考数据",
        # Input labels
        "dau_label":          "日活跃用户数（DAU）",
        "dau_hint":           "例：300M、1.5B、500K",
        "rw_label":           "读写比",
        "rw_hint":            "例：10 表示 10 : 1",
        "writes_label":       "每用户每天写操作次数",
        "data_label":         "每次写请求数据量",
        "retention_label":    "数据保留时长（月）",
        "precision_label":    "精确模式",
        "precision_hint":     "关闭：100,000 秒/天，1000 字节单位",
        "precision_hint_on":  "开启：86,400 秒/天，1024 字节单位",
        # Result labels
        "write_rps_label":    "写 RPS",
        "read_rps_label":     "读 RPS",
        "storage_label":      "存储",
        "result_storage_tpl": (
            "存储：每天新增 {daily}，每月约 {monthly}，总计 {total}。"
        ),
        # Strategy hints
        "hint_high_read":  "读写比高：建议引入缓存与读副本。",
        "hint_high_write": "写多读少：建议使用高吞吐写入存储与最终一致性。",
        # Buttons and actions
        "copy_btn":      "复制分享链接",
        "copied_toast":  "已复制！",
        "invalid_input": "输入无效，请检查标红字段。",
        "too_large":     "数值过大。",
        # Reference table section titles
        "ref_images":    "图片",
        "ref_videos":    "视频",
        "ref_audio":     "音频",
        "ref_bandwidth": "带宽",
        "ref_latency":   "数据存储延迟",
        # Column headers
        "col_quality":   "质量",
        "col_size":      "大小",
        "col_example":   "示例",
        "col_bandwidth": "带宽",
        "col_app":       "应用场景",
        "col_storage":   "存储类型",
        "col_latency":   "延迟",
        "col_note":      "相对速度",
        # Image quality labels
        "img_low":       "低",
        "img_medium":    "中",
        "img_high":      "高",
        "img_vhigh":     "极高",
        # Image examples
        "img_low_ex":    "缩略图、小型网站图片",
        "img_medium_ex": "网站配图",
        "img_high_ex":   "手机拍摄照片",
        "img_vhigh_ex":  "RAW 原始格式照片",
        # Video quality labels
        "vid_low":       "低",
        "vid_medium":    "中",
        "vid_high":      "高",
        # Video examples
        "vid_low_ex":    "480p 视频",
        "vid_medium_ex": "1080p 视频",
        "vid_high_ex":   "4K 视频",
        # Audio quality labels
        "aud_low":       "低",
        "aud_high":      "高",
        # Audio examples
        "aud_low_ex":    "低质量 MP3",
        "aud_high_ex":   "高质量 MP3",
        # Bandwidth app names
        "bw_voip":    "VoIP 语音通话",
        "bw_screen":  "屏幕共享",
        "bw_webinar": "直播 Webinar",
        "bw_720p":    "720p 视频 / Zoom 会议",
        "bw_1080p":   "HD 1080p 流媒体（YouTube / Netflix）",
        "bw_4k":      "4K 超高清视频",
        # Latency storage labels
        "lat_disk":   "硬盘",
        "lat_ssd":    "固态硬盘（SSD）",
        "lat_memory": "内存",
        # Latency notes
        "lat_disk_note": "基准",
        "lat_ssd_note":  "快 15 倍",
        "lat_mem_note":  "快 300 倍",
    },
}

# Verify translation completeness at import time (INV-10)
_en_keys = set(TRANSLATIONS["en"].keys())
_zh_keys = set(TRANSLATIONS["zh"].keys())
_missing_in_zh = _en_keys - _zh_keys
_missing_in_en = _zh_keys - _en_keys
if _missing_in_zh:
    print(f"WARNING: keys missing in zh translation: {_missing_in_zh}", file=sys.stderr)
if _missing_in_en:
    print(f"WARNING: keys missing in en translation: {_missing_in_en}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Domain Layer
# ---------------------------------------------------------------------------

# --- Data models ------------------------------------------------------------

@dataclass
class EstimationParams:
    dau: int
    read_write_ratio: int
    writes_per_user: float
    data_per_write_bytes: int
    retention_months: int
    precision_mode: bool

    @property
    def seconds_per_day(self) -> int:
        return 86_400 if self.precision_mode else 100_000

    @property
    def unit_base(self) -> int:
        return 1024 if self.precision_mode else 1000


@dataclass(frozen=True)
class EstimationResult:
    write_rps: float
    read_rps: float
    daily_storage_bytes: int
    monthly_storage_bytes: int
    total_storage_bytes: int
    unit_base: int

    def __post_init__(self) -> None:
        assert self.write_rps >= 0, "write_rps must be non-negative"
        assert self.read_rps >= self.write_rps, "read_rps must be >= write_rps"
        assert self.daily_storage_bytes >= 0, "daily_storage must be non-negative"
        assert self.monthly_storage_bytes >= self.daily_storage_bytes, \
            "monthly must be >= daily"
        assert self.total_storage_bytes >= self.monthly_storage_bytes, \
            "total must be >= monthly"


@dataclass
class FormattedResult:
    write_rps_str: str
    read_rps_str: str
    daily_str: str
    monthly_str: str
    total_str: str
    description: str
    strategy_hint: str


# --- I18n -------------------------------------------------------------------

class I18n:
    SUPPORTED = ("en", "zh")

    def __init__(self, default_lang: str = "en") -> None:
        self._lang = default_lang if default_lang in self.SUPPORTED else "en"

    def set_language(self, lang: str) -> None:
        if lang not in self.SUPPORTED:
            raise ValueError(f"Unsupported language: {lang!r}. Choose from {self.SUPPORTED}")
        self._lang = lang

    def t(self, key: str) -> str:
        lang_dict = TRANSLATIONS.get(self._lang, {})
        if key in lang_dict:
            return lang_dict[key]
        # Fallback to English (INV-10)
        en_val = TRANSLATIONS["en"].get(key)
        if en_val is not None:
            print(f"WARNING: missing translation key '{key}' for lang '{self._lang}'", file=sys.stderr)
            return en_val
        print(f"WARNING: translation key '{key}' not found in any language", file=sys.stderr)
        return key

    @property
    def current_lang(self) -> str:
        return self._lang


# --- InputParser ------------------------------------------------------------

class InputParser:
    _SUFFIX_MAP = {
        "k": 1_000,
        "m": 1_000_000,
        "b": 1_000_000_000,
        "t": 1_000_000_000_000,
    }
    _DAU_MAX = 100_000_000_000_000  # 100T

    @classmethod
    def parse_dau(cls, raw: str) -> Optional[int]:
        raw = raw.strip()
        if not raw:
            return None
        lower = raw.lower()
        suffix = lower[-1]
        if suffix in cls._SUFFIX_MAP:
            try:
                value = float(lower[:-1])
            except ValueError:
                return None
            result = int(value * cls._SUFFIX_MAP[suffix])
        else:
            try:
                result = int(raw)
            except ValueError:
                try:
                    result = int(float(raw))
                except ValueError:
                    return None
        if result < 1 or result > cls._DAU_MAX:
            return None
        return result

    @classmethod
    def parse_data_size(cls, value: float, unit: str, base: int) -> Optional[int]:
        if value <= 0:
            return None
        unit = unit.upper()
        scales = UNIT_SCALES_1024 if base == 1024 else UNIT_SCALES_1000
        multiplier = None
        for name, mult in scales:
            if name == unit:
                multiplier = mult
                break
        if multiplier is None:
            return None
        try:
            result = int(value * multiplier)
        except OverflowError:
            return None
        if result <= 0:
            return None
        return result

    @classmethod
    def parse_float(cls, raw: str, min_val: float, max_val: float) -> Optional[float]:
        try:
            v = float(raw.strip())
        except ValueError:
            return None
        if v < min_val or v > max_val:
            return None
        return v

    @classmethod
    def parse_int(cls, raw: str, min_val: int, max_val: int) -> Optional[int]:
        try:
            v = int(raw.strip())
        except ValueError:
            try:
                v = int(float(raw.strip()))
            except ValueError:
                return None
        if v < min_val or v > max_val:
            return None
        return v

    @classmethod
    def format_dau(cls, n: int) -> str:
        for suffix, divisor in [("T", 1_000_000_000_000), ("B", 1_000_000_000),
                                  ("M", 1_000_000), ("K", 1_000)]:
            if n >= divisor:
                v = n / divisor
                if v == int(v):
                    return f"{int(v)}{suffix}"
                return f"{v:.1f}{suffix}".rstrip("0").rstrip(".")  + suffix if False else f"{v:.1f}{suffix}"
        return str(n)

    @classmethod
    def encode_params(cls, params: EstimationParams, dau_raw: str,
                      data_val: str, data_unit: str) -> str:
        qs = urlencode({
            "dau":        dau_raw,
            "rw_ratio":   params.read_write_ratio,
            "writes":     params.writes_per_user,
            "data":       data_val,
            "data_unit":  data_unit,
            "retention":  params.retention_months,
            "precision":  1 if params.precision_mode else 0,
        })
        return f"?{qs}"

    @classmethod
    def decode_params(cls, qs: str) -> dict:
        if qs.startswith("?"):
            qs = qs[1:]
        parsed = parse_qs(qs)
        result: dict = {}
        for k, v in parsed.items():
            result[k] = v[0] if v else ""
        return result


# --- Calculator -------------------------------------------------------------

class Calculator:
    @staticmethod
    def compute(params: EstimationParams) -> EstimationResult:
        assert params.seconds_per_day > 0

        write_rps = params.dau * params.writes_per_user / params.seconds_per_day
        read_rps = write_rps * params.read_write_ratio

        daily_bytes = int(params.dau * params.writes_per_user * params.data_per_write_bytes)
        monthly_bytes = daily_bytes * 30
        total_bytes = daily_bytes * params.retention_months * 30

        return EstimationResult(
            write_rps=write_rps,
            read_rps=read_rps,
            daily_storage_bytes=daily_bytes,
            monthly_storage_bytes=monthly_bytes,
            total_storage_bytes=total_bytes,
            unit_base=params.unit_base,
        )


# --- OutputFormatter --------------------------------------------------------

class OutputFormatter:
    @staticmethod
    def format_bytes(n: int, base: int) -> str:
        if n == 0:
            return "0.00 B"
        scales = UNIT_SCALES_1024 if base == 1024 else UNIT_SCALES_1000
        unit_label = "B"
        value = float(n)
        for name, mult in reversed(scales):
            if n >= mult:
                value = n / mult
                unit_label = name
                break
        suffix = "iB" if (base == 1024 and unit_label != "B") else ""
        label = unit_label[0] + suffix if base == 1024 and unit_label != "B" else unit_label
        return f"{value:.2f} {label}"

    @staticmethod
    def format_rps(rps: float) -> str:
        if rps < 0.01:
            return "< 0.01"
        return f"{rps:.2f}"

    @staticmethod
    def format_description(result: EstimationResult, template: str) -> str:
        daily = OutputFormatter.format_bytes(result.daily_storage_bytes, result.unit_base)
        monthly = OutputFormatter.format_bytes(result.monthly_storage_bytes, result.unit_base)
        total = OutputFormatter.format_bytes(result.total_storage_bytes, result.unit_base)
        return template.format(daily=daily, monthly=monthly, total=total)

    @staticmethod
    def strategy_hint(ratio: int, i18n: I18n) -> str:
        if ratio >= 10:
            return i18n.t("hint_high_read")
        if ratio <= 1:
            return i18n.t("hint_high_write")
        return ""

    @classmethod
    def build(cls, result: EstimationResult, i18n: I18n) -> FormattedResult:
        template = i18n.t("result_storage_tpl")
        description = cls.format_description(result, template)
        return FormattedResult(
            write_rps_str=cls.format_rps(result.write_rps),
            read_rps_str=cls.format_rps(result.read_rps),
            daily_str=cls.format_bytes(result.daily_storage_bytes, result.unit_base),
            monthly_str=cls.format_bytes(result.monthly_storage_bytes, result.unit_base),
            total_str=cls.format_bytes(result.total_storage_bytes, result.unit_base),
            description=description,
            strategy_hint="",  # filled by caller with ratio context
        )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def detect_cjk_font() -> str:
    try:
        families = set(tkfont.families())
    except Exception:
        return ""
    for candidate in ["Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC",
                       "Noto Sans CJK", "WenQuanYi Micro Hei", "SimHei"]:
        if candidate in families:
            return candidate
    return ""


# ---------------------------------------------------------------------------
# UI Layer
# ---------------------------------------------------------------------------

# Color palette
C_BG         = "#F8F9FA"
C_PANEL_BG   = "#FFFFFF"
C_BORDER     = "#E2E8F0"
C_LABEL      = "#374151"
C_HINT       = "#9CA3AF"
C_BLUE       = "#2563EB"
C_ORANGE     = "#EA580C"
C_RED_BORDER = "#EF4444"
C_GREEN      = "#059669"
C_BTN_BG     = "#1E40AF"
C_BTN_FG     = "#FFFFFF"
C_SECTION    = "#6366F1"


class InputPanel(ttk.Frame):
    """Left column: all input controls."""

    def __init__(self, parent: tk.Widget, i18n: I18n, on_change, cjk_font: str, **kw):
        super().__init__(parent, **kw)
        self._i18n = i18n
        self._on_change = on_change
        self._cjk_font = cjk_font

        self._text_bindings: list[tuple[tk.Widget, str]] = []

        # StringVars
        self.v_dau       = tk.StringVar(value="300M")
        self.v_rw        = tk.StringVar(value="10")
        self.v_writes    = tk.StringVar(value="1")
        self.v_data      = tk.StringVar(value="50")
        self.v_data_unit = tk.StringVar(value="KB")
        self.v_retention = tk.StringVar(value="120")
        self.v_precision = tk.BooleanVar(value=False)

        self._build()
        self._bind_traces()

    def _build(self) -> None:
        self.configure(style="Card.TFrame")
        self.grid_columnconfigure(0, weight=1)

        row = 0

        # Title
        title = ttk.Label(self, style="SectionTitle.TLabel")
        title.grid(row=row, column=0, sticky="w", padx=16, pady=(16, 12))
        self._bind_text(title, "input_title")
        row += 1

        # DAU
        row = self._add_field(row, "dau_label", self.v_dau, hint_key="dau_hint")
        self._dau_entry = self._last_entry

        # Read:Write Ratio
        row = self._add_field(row, "rw_label", self.v_rw, hint_key="rw_hint")
        self._rw_entry = self._last_entry

        # Writes per user
        row = self._add_field(row, "writes_label", self.v_writes)
        self._writes_entry = self._last_entry

        # Data per write (with unit dropdown)
        row = self._add_data_field(row)

        # Retention
        row = self._add_field(row, "retention_label", self.v_retention)
        self._retention_entry = self._last_entry

        # Precision Mode
        row = self._add_precision(row)

        # Spacer
        spacer = ttk.Frame(self, style="Card.TFrame", height=8)
        spacer.grid(row=row, column=0, sticky="ew")
        row += 1

    def _add_field(self, row: int, label_key: str, var: tk.StringVar,
                   hint_key: str = "") -> int:
        lbl = ttk.Label(self, style="FieldLabel.TLabel")
        lbl.grid(row=row, column=0, sticky="w", padx=16, pady=(10, 0))
        self._bind_text(lbl, label_key)
        row += 1

        entry = ttk.Entry(self, textvariable=var, font=("Courier", 13), width=28)
        entry.grid(row=row, column=0, sticky="ew", padx=16, pady=(2, 0))
        self._last_entry = entry
        row += 1

        if hint_key:
            hint = ttk.Label(self, style="Hint.TLabel")
            hint.grid(row=row, column=0, sticky="w", padx=16, pady=(1, 0))
            self._bind_text(hint, hint_key)
            row += 1

        return row

    def _add_data_field(self, row: int) -> int:
        lbl = ttk.Label(self, style="FieldLabel.TLabel")
        lbl.grid(row=row, column=0, sticky="w", padx=16, pady=(10, 0))
        self._bind_text(lbl, "data_label")
        row += 1

        frame = ttk.Frame(self, style="Card.TFrame")
        frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(2, 0))
        frame.grid_columnconfigure(0, weight=1)

        entry = ttk.Entry(frame, textvariable=self.v_data, font=("Courier", 13))
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._data_entry = entry
        self._last_entry = entry

        dropdown = ttk.Combobox(frame, textvariable=self.v_data_unit,
                                values=DATA_UNITS, state="readonly", width=6,
                                font=("Courier", 13))
        dropdown.grid(row=0, column=1)
        self._unit_dropdown = dropdown

        row += 1
        return row

    def _add_precision(self, row: int) -> int:
        frame = ttk.Frame(self, style="Card.TFrame")
        frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(14, 0))

        cb = ttk.Checkbutton(frame, variable=self.v_precision,
                             style="Precision.TCheckbutton")
        cb.grid(row=0, column=0, padx=(0, 8))
        self._precision_cb = cb

        lbl = ttk.Label(frame, style="FieldLabel.TLabel")
        lbl.grid(row=0, column=1, sticky="w")
        self._bind_text(lbl, "precision_label")

        row += 1

        hint = ttk.Label(self, style="Hint.TLabel")
        hint.grid(row=row, column=0, sticky="w", padx=16, pady=(2, 0))
        self._precision_hint_lbl = hint
        self._update_precision_hint()
        row += 1

        return row

    def _update_precision_hint(self) -> None:
        key = "precision_hint_on" if self.v_precision.get() else "precision_hint"
        self._precision_hint_lbl.config(text=self._i18n.t(key))

    def _bind_traces(self) -> None:
        for var in [self.v_rw, self.v_writes, self.v_data,
                    self.v_data_unit, self.v_retention]:
            var.trace_add("write", self._trace_change)

        self.v_dau.trace_add("write", self._trace_change)
        self.v_precision.trace_add("write", self._precision_changed)

        # DAU blur/enter for reformatting
        self._dau_entry.bind("<FocusOut>", self._reformat_dau)
        self._dau_entry.bind("<Return>",   self._reformat_dau)

    def _trace_change(self, *_) -> None:
        self._on_change()

    def _precision_changed(self, *_) -> None:
        self._update_precision_hint()
        self._on_change()

    def _reformat_dau(self, *_) -> None:
        n = InputParser.parse_dau(self.v_dau.get())
        if n is not None:
            self.v_dau.set(InputParser.format_dau(n))
        self._on_change()

    def get_params(self) -> Optional[EstimationParams]:
        base = 1024 if self.v_precision.get() else 1000
        errors: list[str] = []

        dau = InputParser.parse_dau(self.v_dau.get())
        rw  = InputParser.parse_int(self.v_rw.get(), 1, 1000)
        wr  = InputParser.parse_float(self.v_writes.get(), 0.001, 10_000)
        dt  = InputParser.parse_float(self.v_data.get(), 0.0, 1e30)
        dt_bytes = None
        if dt is not None:
            dt_bytes = InputParser.parse_data_size(dt, self.v_data_unit.get(), base)
        ret = InputParser.parse_int(self.v_retention.get(), 1, 1200)

        self._set_entry_state(self._dau_entry,      dau is not None)
        self._set_entry_state(self._rw_entry,       rw  is not None)
        self._set_entry_state(self._writes_entry,   wr  is not None)
        self._set_entry_state(self._data_entry,     dt_bytes is not None)
        self._set_entry_state(self._retention_entry, ret is not None)

        if any(v is None for v in [dau, rw, wr, dt_bytes, ret]):
            return None

        return EstimationParams(
            dau=dau,
            read_write_ratio=rw,
            writes_per_user=wr,
            data_per_write_bytes=dt_bytes,
            retention_months=ret,
            precision_mode=self.v_precision.get(),
        )

    def _set_entry_state(self, entry: ttk.Entry, valid: bool) -> None:
        style_name = "Valid.TEntry" if valid else "Invalid.TEntry"
        try:
            entry.configure(style=style_name)
        except Exception:
            pass

    def get_raw_data_fields(self) -> tuple[str, str]:
        return self.v_data.get(), self.v_data_unit.get()

    def get_raw_dau(self) -> str:
        return self.v_dau.get()

    def restore_params(self, d: dict) -> None:
        if "dau" in d:
            self.v_dau.set(d["dau"])
        if "rw_ratio" in d:
            self.v_rw.set(d["rw_ratio"])
        if "writes" in d:
            self.v_writes.set(d["writes"])
        if "data" in d:
            self.v_data.set(d["data"])
        if "data_unit" in d:
            unit = d["data_unit"].upper()
            if unit in DATA_UNITS:
                self.v_data_unit.set(unit)
        if "retention" in d:
            self.v_retention.set(d["retention"])
        if "precision" in d:
            self.v_precision.set(d["precision"] == "1")

    # Text binding registry for language refresh
    def _bind_text(self, widget: tk.Widget, key: str) -> None:
        self._text_bindings.append((widget, key))
        widget.config(text=self._i18n.t(key))

    def refresh_texts(self) -> None:
        for widget, key in self._text_bindings:
            try:
                widget.config(text=self._i18n.t(key))
            except Exception:
                pass
        self._update_precision_hint()


class ResultPanel(ttk.Frame):
    """Right column upper: RPS values, storage description, strategy hint."""

    def __init__(self, parent: tk.Widget, i18n: I18n, cjk_font: str, **kw):
        super().__init__(parent, **kw)
        self._i18n = i18n
        self._cjk_font = cjk_font
        self._last_result: Optional[EstimationResult] = None
        self._text_bindings: list[tuple[tk.Widget, str]] = []
        self._build()

    def _build(self) -> None:
        self.configure(style="Card.TFrame")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        row = 0

        # Title
        title = ttk.Label(self, style="SectionTitle.TLabel")
        title.grid(row=row, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 12))
        self._bind_text(title, "result_title")
        row += 1

        # Write RPS card
        self._write_rps_lbl = self._make_metric_card(row, 0, "write_rps_label", C_BLUE)
        # Read RPS card
        self._read_rps_lbl = self._make_metric_card(row, 1, "read_rps_label", C_ORANGE)
        row += 3  # card takes 3 rows internally (label, value, spacer)

        # Separator
        sep = ttk.Separator(self, orient="horizontal")
        sep.grid(row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=8)
        row += 1

        # Storage description
        self._storage_lbl = ttk.Label(self, style="Description.TLabel",
                                       wraplength=440, justify="left")
        self._storage_lbl.grid(row=row, column=0, columnspan=2,
                                sticky="w", padx=16, pady=(0, 4))
        row += 1

        # Strategy hint
        self._hint_lbl = ttk.Label(self, style="Hint.TLabel",
                                    wraplength=440, justify="left")
        self._hint_lbl.grid(row=row, column=0, columnspan=2,
                             sticky="w", padx=16, pady=(0, 16))
        row += 1

    def _make_metric_card(self, row: int, col: int,
                           label_key: str, color: str) -> ttk.Label:
        inner = ttk.Frame(self, style="Metric.TFrame")
        inner.grid(row=row, column=col, sticky="nsew", padx=(16 if col == 0 else 8, 8 if col == 0 else 16), pady=4)
        inner.grid_columnconfigure(0, weight=1)

        lbl = ttk.Label(inner, style="MetricLabel.TLabel")
        lbl.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 0))
        self._bind_text(lbl, label_key)

        val_lbl = ttk.Label(inner, text="", font=("Courier", 26, "bold"),
                             foreground=color, background=C_PANEL_BG)
        val_lbl.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))
        return val_lbl

    def render(self, result: EstimationResult, ratio: int) -> None:
        self._last_result = result
        fmt = OutputFormatter.build(result, self._i18n)

        self._write_rps_lbl.config(text=fmt.write_rps_str)
        self._read_rps_lbl.config(text=fmt.read_rps_str)
        self._storage_lbl.config(text=fmt.description)

        hint = OutputFormatter.strategy_hint(ratio, self._i18n)
        self._hint_lbl.config(text=hint)

    def render_error(self) -> None:
        self._last_result = None
        msg = self._i18n.t("invalid_input")
        self._write_rps_lbl.config(text="---")
        self._read_rps_lbl.config(text="---")
        self._storage_lbl.config(text=msg)
        self._hint_lbl.config(text="")

    def _rerender_description(self) -> None:
        if self._last_result is None:
            self._storage_lbl.config(text=self._i18n.t("invalid_input"))
            return
        template = self._i18n.t("result_storage_tpl")
        desc = OutputFormatter.format_description(self._last_result, template)
        self._storage_lbl.config(text=desc)

    def _bind_text(self, widget: tk.Widget, key: str) -> None:
        self._text_bindings.append((widget, key))
        widget.config(text=self._i18n.t(key))

    def refresh_texts(self) -> None:
        for widget, key in self._text_bindings:
            try:
                widget.config(text=self._i18n.t(key))
            except Exception:
                pass
        self._rerender_description()


class ReferencePanel(ttk.Frame):
    """Right column lower: scrollable five-table reference area."""

    def __init__(self, parent: tk.Widget, i18n: I18n, cjk_font: str, **kw):
        super().__init__(parent, **kw)
        self._i18n = i18n
        self._cjk_font = cjk_font
        self._title_bindings: list[tuple[tk.Widget, str]] = []
        self._trees: list[tuple[ttk.Treeview, list[str]]] = []  # (tree, col_keys)
        self._tree_data: list[dict] = []  # stored for re-render on lang switch
        self._build()

    def _build(self) -> None:
        self.configure(style="Card.TFrame")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        title = ttk.Label(self, style="SectionTitle.TLabel")
        title.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 8))
        self._title_bindings.append((title, "ref_title"))
        title.config(text=self._i18n.t("ref_title"))

        # Scrollable container
        canvas = tk.Canvas(self, background=C_PANEL_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

        self._scroll_frame = ttk.Frame(canvas, style="Card.TFrame")
        self._scroll_frame.grid_columnconfigure(0, weight=1)
        self._canvas_window = canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")

        self._scroll_frame.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(
            self._canvas_window, width=e.width))

        # Mouse wheel
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))

        self._canvas = canvas
        self._render_tables()

    def _render_tables(self) -> None:
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()
        self._trees.clear()

        sections = [
            ("ref_images",    "images",    ["col_quality", "col_size", "col_example"]),
            ("ref_videos",    "videos",    ["col_quality", "col_size", "col_example"]),
            ("ref_audio",     "audio",     ["col_quality", "col_size", "col_example"]),
            ("ref_bandwidth", "bandwidth", ["col_bandwidth", "col_app"]),
            ("ref_latency",   "latency",   ["col_storage", "col_latency", "col_note"]),
        ]

        row = 0
        for title_key, data_key, col_keys in sections:
            # Section title
            lbl = ttk.Label(self._scroll_frame, text=self._i18n.t(title_key),
                            style="RefSectionTitle.TLabel")
            lbl.grid(row=row, column=0, sticky="w", padx=12, pady=(12, 4))
            self._title_bindings.append((lbl, title_key))
            row += 1

            # Build treeview
            col_ids = [f"c{i}" for i in range(len(col_keys))]
            tree = ttk.Treeview(self._scroll_frame, columns=col_ids,
                                show="headings", height=len(REFERENCE_DATA[data_key]))

            for i, (col_id, col_key) in enumerate(zip(col_ids, col_keys)):
                tree.heading(col_id, text=self._i18n.t(col_key))
                tree.column(col_id, width=160 if i > 0 else 100, stretch=True)

            self._populate_tree(tree, data_key, col_keys)
            tree.grid(row=row, column=0, sticky="ew", padx=12, pady=(0, 4))
            self._trees.append((tree, col_keys, data_key, col_ids))
            row += 1

    def _populate_tree(self, tree: ttk.Treeview, data_key: str,
                       col_keys: list[str]) -> None:
        for item in tree.get_children():
            tree.delete(item)

        rows = REFERENCE_DATA[data_key]
        for entry in rows:
            values = self._entry_to_values(entry, col_keys, data_key)
            tree.insert("", "end", values=values)

    def _entry_to_values(self, entry: dict, col_keys: list[str], data_key: str) -> tuple:
        values = []
        if data_key in ("images", "videos", "audio"):
            values.append(self._i18n.t(entry["quality_key"]))
            values.append(entry["size"])
            values.append(self._i18n.t(entry["example_key"]))
        elif data_key == "bandwidth":
            values.append(entry["bw"])
            values.append(self._i18n.t(entry["app_key"]))
        elif data_key == "latency":
            values.append(self._i18n.t(entry["storage_key"]))
            values.append(entry["latency"])
            values.append(self._i18n.t(entry["note_key"]))
        return tuple(values)

    def refresh_texts(self) -> None:
        for widget, key in self._title_bindings:
            try:
                widget.config(text=self._i18n.t(key))
            except Exception:
                pass
        # Re-populate trees
        sections = [
            ("images",    ["col_quality", "col_size", "col_example"]),
            ("videos",    ["col_quality", "col_size", "col_example"]),
            ("audio",     ["col_quality", "col_size", "col_example"]),
            ("bandwidth", ["col_bandwidth", "col_app"]),
            ("latency",   ["col_storage", "col_latency", "col_note"]),
        ]
        for (tree, col_keys, data_key, col_ids), (_, s_col_keys) in zip(self._trees, sections):
            for col_id, col_key in zip(col_ids, col_keys):
                tree.heading(col_id, text=self._i18n.t(col_key))
            self._populate_tree(tree, data_key, col_keys)


class AppWindow:
    """Main application window — composes all panels."""

    def __init__(self, root: tk.Tk, i18n: I18n, initial_params: Optional[dict] = None):
        self._root = root
        self._i18n = i18n
        self._last_ratio = 10
        self._cjk_font = detect_cjk_font()

        self._setup_styles()
        self._build(initial_params)

    def _setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame",        background=C_BG)
        style.configure("Card.TFrame",   background=C_PANEL_BG)
        style.configure("Metric.TFrame", background=C_PANEL_BG,
                        relief="solid", borderwidth=1)

        font_family = self._cjk_font if self._cjk_font else "Helvetica"

        style.configure("SectionTitle.TLabel", background=C_PANEL_BG,
                        foreground=C_SECTION, font=(font_family, 13, "bold"))
        style.configure("FieldLabel.TLabel",   background=C_PANEL_BG,
                        foreground=C_LABEL,   font=(font_family, 11))
        style.configure("Hint.TLabel",         background=C_PANEL_BG,
                        foreground=C_HINT,    font=(font_family, 9))
        style.configure("Description.TLabel",  background=C_PANEL_BG,
                        foreground=C_LABEL,   font=(font_family, 11))
        style.configure("MetricLabel.TLabel",  background=C_PANEL_BG,
                        foreground=C_HINT,    font=(font_family, 10))
        style.configure("RefSectionTitle.TLabel", background=C_PANEL_BG,
                        foreground=C_LABEL,   font=(font_family, 11, "bold"))

        style.configure("Valid.TEntry",   fieldbackground="white")
        style.configure("Invalid.TEntry", fieldbackground="#FEE2E2")

        style.configure("LangBtn.TButton", font=(font_family, 10, "bold"),
                        padding=(8, 4))
        style.configure("CopyBtn.TButton", font=(font_family, 10),
                        padding=(10, 5), background=C_BTN_BG, foreground=C_BTN_FG)

        style.configure("Treeview",       font=(font_family, 10),
                        rowheight=24,     background=C_PANEL_BG,
                        fieldbackground=C_PANEL_BG)
        style.configure("Treeview.Heading", font=(font_family, 10, "bold"))

    def _build(self, initial_params: Optional[dict]) -> None:
        self._root.title(self._i18n.t("app_title"))
        self._root.minsize(900, 600)
        self._root.configure(background=C_BG)

        self._root.grid_rowconfigure(1, weight=1)
        self._root.grid_columnconfigure(0, weight=1)

        # Header bar
        self._build_header()

        # Main content
        content = ttk.Frame(self._root, style="TFrame")
        content.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=2, minsize=320)
        content.grid_columnconfigure(1, weight=3, minsize=460)

        # Left: input panel
        self._input_panel = InputPanel(
            content, self._i18n, self._on_change, self._cjk_font,
            style="Card.TFrame"
        )
        self._input_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        # Right column
        right = ttk.Frame(content, style="TFrame")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.grid_rowconfigure(0, weight=0)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._result_panel = ResultPanel(right, self._i18n, self._cjk_font,
                                          style="Card.TFrame")
        self._result_panel.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self._ref_panel = ReferencePanel(right, self._i18n, self._cjk_font,
                                          style="Card.TFrame")
        self._ref_panel.grid(row=1, column=0, sticky="nsew")

        # Restore params if provided
        if initial_params:
            self._input_panel.restore_params(initial_params)

        # Initial calculation
        self._on_change()

    def _build_header(self) -> None:
        header = ttk.Frame(self._root, style="TFrame")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)

        font_family = self._cjk_font if self._cjk_font else "Helvetica"

        self._title_lbl = tk.Label(header, text=self._i18n.t("app_title"),
                                    font=(font_family, 16, "bold"),
                                    background=C_BG, foreground="#1E293B")
        self._title_lbl.grid(row=0, column=0, sticky="w")

        btn_frame = ttk.Frame(header, style="TFrame")
        btn_frame.grid(row=0, column=1, sticky="e")

        # Language buttons
        self._btn_en = ttk.Button(btn_frame, text="EN",
                                   style="LangBtn.TButton",
                                   command=lambda: self._set_lang("en"))
        self._btn_en.grid(row=0, column=0, padx=(0, 4))

        self._btn_zh = ttk.Button(btn_frame, text="中文",
                                   style="LangBtn.TButton",
                                   command=lambda: self._set_lang("zh"))
        self._btn_zh.grid(row=0, column=1, padx=(0, 12))

        # Copy link button
        self._copy_btn = ttk.Button(btn_frame, text=self._i18n.t("copy_btn"),
                                     style="CopyBtn.TButton",
                                     command=self._copy_link)
        self._copy_btn.grid(row=0, column=2)

        # Toast label (hidden by default)
        font_family2 = self._cjk_font if self._cjk_font else "Helvetica"
        self._toast_lbl = tk.Label(header, text="", font=(font_family2, 10),
                                    background=C_BG, foreground=C_GREEN)
        self._toast_lbl.grid(row=1, column=1, sticky="e", pady=(2, 0))

    def _on_change(self) -> None:
        params = self._input_panel.get_params()
        if params is None:
            self._result_panel.render_error()
            return
        self._last_ratio = params.read_write_ratio
        result = Calculator.compute(params)
        self._result_panel.render(result, params.read_write_ratio)

    def _set_lang(self, lang: str) -> None:
        self._i18n.set_language(lang)
        font_family = self._cjk_font if self._cjk_font else "Helvetica"
        self._title_lbl.config(text=self._i18n.t("app_title"))
        self._copy_btn.config(text=self._i18n.t("copy_btn"))
        self._input_panel.refresh_texts()
        self._result_panel.refresh_texts()
        self._ref_panel.refresh_texts()

    def _copy_link(self) -> None:
        params = self._input_panel.get_params()
        if params is None:
            return
        dau_raw = self._input_panel.get_raw_dau()
        data_val, data_unit = self._input_panel.get_raw_data_fields()
        qs = InputParser.encode_params(params, dau_raw, data_val, data_unit)

        self._root.clipboard_clear()
        self._root.clipboard_append(qs)

        self._toast_lbl.config(text=self._i18n.t("copied_toast"))
        self._root.after(2000, lambda: self._toast_lbl.config(text=""))


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Back-of-the-Envelope Resource Estimator"
    )
    parser.add_argument(
        "--lang", choices=["en", "zh"], default="en",
        help="UI language (default: en)"
    )
    parser.add_argument(
        "--params", default="",
        help='Restore parameters from a shareable query string, e.g. "?dau=300M&..."'
    )
    args = parser.parse_args()

    initial_params: Optional[dict] = None
    if args.params:
        try:
            initial_params = InputParser.decode_params(args.params)
        except Exception:
            print("WARNING: could not parse --params value; using defaults.", file=sys.stderr)

    i18n = I18n(default_lang=args.lang)

    root = tk.Tk()
    root.title("Back-of-the-Envelope Resource Estimator")

    AppWindow(root, i18n, initial_params=initial_params)

    root.mainloop()


if __name__ == "__main__":
    main()
