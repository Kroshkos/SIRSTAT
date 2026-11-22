# -*- coding: utf-8 -*-
"""
pdf_report.py — PDF-отчёт для руководителя (SIRSTAT).
Формат: A4, альбомная ориентация. Дизайн согласован с фирменной палитрой
интерфейса и тепловой шкалой листов Excel.

Исправления v4:
  • наложение donut/бары на стр. 2 — разнесены (0.045+0.26 vs 0.48+0.48)
  • длинные названия выходят за левый край (стр. 3, 4, 5) — left=0.22
  • полные названия микробов/антибиотиков на стр. 1 (без _short)
  • защита от 'str' object has no attribute 'size' через _to_series
  • ffill().bfill() вместо fillna(method=...)
"""
import os
import warnings
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Rectangle
import matplotlib.gridspec as gridspec

from app_core import (
    load_data, categorize_material, DEFAULT_CLINIC_LABEL,
)

warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

# ============================================================
# ПАЛИТРА (согласована с SIRSTAT: 1.py / app_core.py)
# ============================================================
INK        = '#0F172A'
PRIMARY    = '#1F4E79'
ACCENT     = '#2CC98F'
ACCENT_DK  = '#1E8E6A'
DANGER     = '#E35D4A'
WARNING    = '#F59E0B'
MUTED      = '#94A3B8'
HAIRLINE   = '#E2E8F0'
PAPER      = '#FFFFFF'
PAPER_ALT  = '#F8FAFC'

# Тепловая шкала S% — идентична CMP_SCALES из app_core.py
S_HEAT = [
    (80.0, '#C6EFCE', '#006100'),
    (60.0, '#E2F0D9', '#375623'),
    (40.0, '#FFEB9C', '#9C6500'),
    (20.0, '#FFCC99', '#974706'),
    ( 0.0, '#FFC7CE', '#9C0006'),
]

CAT_PALETTE = ['#1F4E79', '#2CC98F', '#3B82F6', '#F59E0B', '#E35D4A',
               '#8B5CF6', '#06B6D4', '#EC4899', '#10B981', '#6366F1']

FIGSIZE = (11.69, 8.27)   # A4 landscape
DPI = 150


# ============================================================
# СЛУЖЕБНОЕ
# ============================================================
def _setup_fonts():
    for name in ('Segoe UI', 'DejaVu Sans', 'Arial', 'Helvetica'):
        try:
            from matplotlib.font_manager import fontManager
            if any(f.name == name for f in fontManager.ttflist):
                plt.rcParams['font.family'] = name
                break
        except Exception:
            continue
    plt.rcParams.update({
        'axes.unicode_minus': False,
        'font.size': 9.5,
        'axes.labelcolor': INK,
        'xtick.color': MUTED,
        'ytick.color': INK,
        'axes.edgecolor': HAIRLINE,
    })


def _s_heat(pct: float):
    """(заливка, текст) для значения S%."""
    for th, fg, fc in S_HEAT:
        if pct >= th:
            return fg, fc
    return S_HEAT[-1][1], S_HEAT[-1][2]


def _short(s, n=26):
    s = str(s)
    return s if len(s) <= n else s[:n - 1] + '…'


def _pct(num, den):
    return round(num / den * 100, 1) if den else 0.0


def _to_series(obj, name='value'):
    """Приводит результат pandas к одноимённому Series (защита от строк)."""
    if isinstance(obj, pd.DataFrame):
        if obj.shape[1] == 1:
            obj = obj.iloc[:, 0]
        else:
            obj = obj.sum(axis=1)
    if not isinstance(obj, pd.Series):
        obj = pd.Series(obj)
    obj = obj.dropna().astype('int64')
    obj.index = [str(i) for i in obj.index]
    return obj.sort_values(ascending=False)


def _page_shell(fig, title, subtitle):
    """Единый каркас страницы: акцентная полоса + заголовок + разделитель."""
    fig.patches.append(Rectangle(
        (0, 0.965), 1, 0.035,
        transform=fig.transFigure, facecolor=PRIMARY, edgecolor='none', zorder=5))
    fig.patches.append(Rectangle(
        (0, 0.965), 0.06, 0.035,
        transform=fig.transFigure, facecolor=ACCENT, edgecolor='none', zorder=6))
    fig.text(0.045, 0.915, title, fontsize=17, fontweight='bold',
             color=PRIMARY, va='center')
    fig.text(0.045, 0.885, subtitle, fontsize=9.5, color=MUTED, va='center')
    fig.patches.append(Rectangle(
        (0.045, 0.862), 0.92, 0.0012,
        transform=fig.transFigure, facecolor=HAIRLINE, edgecolor='none'))


def _page_footer(fig, n, total, period):
    fig.text(0.045, 0.035, "SIRSTAT · аналитический отчёт",
             fontsize=7.5, color=MUTED, va='center')
    fig.text(0.5, 0.035, period, fontsize=7.5, color=MUTED,
             va='center', ha='center')
    fig.text(0.955, 0.035, f"{n} / {total}", fontsize=7.5, color=MUTED,
             va='center', ha='right')


def _new_figure():
    fig = plt.figure(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor(PAPER)
    return fig


def _clean_axes(ax, grid_axis='x'):
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(HAIRLINE)
    ax.tick_params(axis='both', length=0, labelsize=8.5)
    if grid_axis:
        ax.grid(axis=grid_axis, color=HAIRLINE, linestyle='-', linewidth=0.7, alpha=0.9)
        ax.set_axisbelow(True)


def _wrap(text, width):
    words, lines, cur = text.split(), [], ''
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur); cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur:
        lines.append(cur)
    return lines


# ============================================================
# АГРЕГАЦИЯ ДАННЫХ (с гарантиями типов)
# ============================================================
def _compute_report_data(data, antibiotics, ab_indices):
    report = {}
    total = len(data)

    if total == 0:
        report['period'] = 'нет данных'
        report['kpi'] = {'Пациентов': 0, 'Всего проб': 0, 'С ростом': 0,
                         '% положительных': 0.0, 'Диагностичных': 0,
                         '% диагностичных': 0.0}
        for k in ('categories', 'top_materials', 'top_organisms'):
            report[k] = pd.Series(dtype='int64')
        for k in ('ab_worst', 'ab_best', 'org_worst', 'monthly', 'clinics'):
            report[k] = pd.DataFrame()
        return report

    pos = int(data['is_positive'].sum())
    diag = int((data['is_positive'] & data['diagnostic']).sum())
    patients = int(data['patient_id'].nunique())
    dates = data['date'].dropna()
    period = (f"{dates.min():%d.%m.%Y} — {dates.max():%d.%m.%Y}"
              if not dates.empty else 'период не определён')

    report['period'] = period
    report['kpi'] = {
        'Пациентов': patients,
        'Всего проб': total,
        'С ростом': pos,
        '% положительных': _pct(pos, total),
        'Диагностичных': diag,
        '% диагностичных': _pct(diag, pos),
    }

    df = data.copy()
    df['category'] = df['material_raw'].apply(
        lambda x: categorize_material(str(x) if pd.notna(x) else 'прочее')[0])

    report['categories'] = _to_series(df['category'].value_counts())
    report['top_materials'] = _to_series(
        df['material_raw'].astype(str).str.strip().value_counts().head(10))

    pos_df = df[df['is_positive']]
    report['top_organisms'] = _to_series(
        pos_df['organism'].astype(str).str.strip().value_counts().head(10))

    # --- S% по антибиотикам ---
    ab_rows = []
    for ab in antibiotics:
        try:
            col_i = ab_indices[antibiotics.index(ab)]
        except (ValueError, IndexError):
            continue
        vals = df.iloc[:, col_i].dropna().astype(str).str.upper().str.strip()
        s = int((vals == 'S').sum()); i_ = int((vals == 'I').sum())
        r = int((vals == 'R').sum())
        n = s + i_ + r
        if n < 5:
            continue
        ab_rows.append({'antibiotic': str(ab), 'S%': round((s + i_) / n * 100, 1),
                        'n': n, 'S': s, 'I': i_, 'R': r})
    ab_df = pd.DataFrame(ab_rows)
    report['ab_worst'] = ab_df.nsmallest(10, 'S%') if not ab_df.empty else pd.DataFrame()
    report['ab_best'] = ab_df.nlargest(10, 'S%') if not ab_df.empty else pd.DataFrame()

    # --- S% по микроорганизмам ---
    org_rows = []
    for org in pos_df['organism'].dropna().unique():
        sub = pos_df[pos_df['organism'] == org]
        s = i_ = r = 0
        for col_i in ab_indices:
            v = sub.iloc[:, col_i].dropna().astype(str).str.upper().str.strip()
            s += int((v == 'S').sum()); i_ += int((v == 'I').sum())
            r += int((v == 'R').sum())
        n = s + i_ + r
        if n < 10:
            continue
        org_rows.append({'organism': str(org), 'S%': round((s + i_) / n * 100, 1),
                         'n': n, 'count': len(sub)})
    org_df = pd.DataFrame(org_rows)
    report['org_worst'] = org_df.nsmallest(8, 'S%') if not org_df.empty else pd.DataFrame()

    # --- динамика ---
    if 'date' in df.columns:
        d = df[df['date'].notna()].copy()
        if not d.empty:
            d['ym'] = d['date'].dt.to_period('M')
            m = d.groupby('ym').agg(total=('is_positive', 'size'),
                                    pos=('is_positive', 'sum')).reset_index()
            m['pct_pos'] = (m['pos'] / m['total'] * 100).round(1)
            sp = []
            for _, g in d.groupby('ym'):
                s = i_ = r = 0
                for col_i in ab_indices:
                    v = g.iloc[:, col_i].dropna().astype(str).str.upper().str.strip()
                    s += int((v == 'S').sum()); i_ += int((v == 'I').sum())
                    r += int((v == 'R').sum())
                nn = s + i_ + r
                sp.append(round((s + i_) / nn * 100, 1) if nn else np.nan)
            m['S%'] = sp
            m['ym_str'] = m['ym'].astype(str)
            report['monthly'] = m.tail(14)
        else:
            report['monthly'] = pd.DataFrame()
    else:
        report['monthly'] = pd.DataFrame()

    # --- клиники ---
    if 'clinic' in df.columns:
        cl_list = [c for c in df['clinic'].dropna().astype(str).str.strip().unique()
                   if c and c != DEFAULT_CLINIC_LABEL]
        rows = []
        for cl in cl_list:
            sub = df[df['clinic'].astype(str).str.strip() == cl]
            s = i_ = r = 0
            for col_i in ab_indices:
                v = sub.iloc[:, col_i].dropna().astype(str).str.upper().str.strip()
                s += int((v == 'S').sum()); i_ += int((v == 'I').sum())
                r += int((v == 'R').sum())
            n = s + i_ + r
            if n >= 10:
                rows.append({'clinic': cl, 'S%': round((s + i_) / n * 100, 1),
                             'n': n, 'samples': len(sub)})
        cl_df = pd.DataFrame(rows)
        report['clinics'] = cl_df.sort_values('S%', ascending=False) if not cl_df.empty else pd.DataFrame()
    else:
        report['clinics'] = pd.DataFrame()

    return report


# ============================================================
# СТРАНИЦА 1 — СВОДКА
# ============================================================
def _build_bullets(report):
    """Формирует 4–5 коротких выводов для обложки.
    Названия микроорганизмов и антибиотиков НЕ обрезаются —
    руководитель должен видеть полные имена."""
    out = []
    kpi = report['kpi']
    out.append(('info', f"{kpi['Всего проб']} проб от {kpi['Пациентов']} пациентов; "
                        f"{kpi['С ростом']} с ростом, {kpi['% диагностичных']}% в диагностическом титре."))

    ab_worst = report['ab_worst']
    if not ab_worst.empty:
        # ПОЛНЫЕ названия — без _short()
        names = ', '.join(str(a) for a in ab_worst['antibiotic'].head(3))
        out.append(('bad', f"Наименьшая чувствительность: {names} — "
                           f"риск неэффективной эмпирической терапии."))

    ab_best = report['ab_best']
    if not ab_best.empty:
        names = ', '.join(str(a) for a in ab_best['antibiotic'].head(3))
        out.append(('ok', f"Максимальная чувствительность сохраняется к: {names}."))

    org_worst = report['org_worst']
    if not org_worst.empty:
        # ПОЛНЫЕ названия микроорганизмов
        names = ', '.join(str(o) for o in org_worst['organism'].head(2))
        out.append(('warn', f"Наиболее устойчивые микроорганизмы: {names}."))

    cl = report['clinics']
    if not cl.empty and len(cl) >= 2:
        best, worst = cl.iloc[0], cl.iloc[-1]
        out.append(('warn', f"Разброс по клиникам: {best['clinic']} "
                            f"({best['S%']}%) против {worst['clinic']} ({worst['S%']}%)."))
    return out

def _page_summary(fig, report):
    _page_shell(fig, 'Сводка ключевых показателей',
                f"Период анализа: {report['period']}")

    kpi = report['kpi']
    items = list(kpi.items())

    # 6 карточек: 3 колонки × 2 ряда, занимают 68% ширины
    gs = gridspec.GridSpec(2, 3, figure=fig,
                  left=0.045, right=0.70, top=0.82, bottom=0.22,
                  wspace=0.10, hspace=0.32)

    accents = [PRIMARY, ACCENT, PRIMARY, ACCENT, PRIMARY, ACCENT]
    for i, (label, value) in enumerate(items):
        r, c = i // 3, i % 3
        ax = fig.add_subplot(gs[r, c])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
        # подложка
        ax.add_patch(FancyBboxPatch((0.0, 0.0), 1.0, 1.0,
                     boxstyle='round,pad=0.008,rounding_size=0.03',
                     facecolor=PAPER_ALT, edgecolor='none',
                     transform=ax.transAxes, zorder=1))
        # акцентная полоса слева
        ax.add_patch(Rectangle((0.0, 0.0), 0.018, 1.0,
                     facecolor=accents[i], edgecolor='none',
                     transform=ax.transAxes, zorder=2))
        val_txt = f"{value:.1f}%" if isinstance(value, float) else f"{int(value):,}".replace(',', ' ')
        ax.text(0.09, 0.62, val_txt, fontsize=26, fontweight='bold',
                color=accents[i], va='center', ha='left', transform=ax.transAxes)
        ax.text(0.09, 0.22, label, fontsize=10, color=MUTED,
                va='center', ha='left', transform=ax.transAxes)

    # Правая колонка — «Что важно»
    # СДВИНУТА ЛЕВЕЕ: 0.735 → 0.72 (чтобы текст не выходил за правый край)
    fig.text(0.72, 0.82, 'Что важно', fontsize=12, fontweight='bold', color=PRIMARY)
    fig.patches.append(Rectangle((0.72, 0.812), 0.22, 0.002,
                 transform=fig.transFigure, facecolor=ACCENT, edgecolor='none'))

    bullets = _build_bullets(report)
    y = 0.775
    for kind, text in bullets:
        color = {'ok': ACCENT_DK, 'warn': WARNING, 'bad': DANGER, 'info': PRIMARY}[kind]
        marker = '●'
        # СДВИНУТА ЛЕВЕЕ: 0.735 → 0.72
        fig.text(0.72, y, marker, fontsize=9, color=color, va='top')
        # УМЕНЬШЕНА ШИРИНА ПЕРЕНОСА: 52 → 42 (чтобы текст помещался)
        wrapped = _wrap(text, 42)
        for li, line in enumerate(wrapped):
            # СДВИНУТА ЛЕВЕЕ: 0.755 → 0.735
            fig.text(0.735, y - li * 0.028, line, fontsize=9.2,
                     color=INK, va='top')
        y -= 0.028 * len(wrapped) + 0.045

    # нижняя плашка-интерпретация
    pct = kpi['% положительных']
    verdict = ('Выявляемость на хорошем уровне' if pct >= 50 else
               'Выявляемость средняя — есть резерв' if pct >= 30 else
               'Низкая выявляемость — пересмотреть забор материала')
    fig.patches.append(FancyBboxPatch((0.045, 0.10), 0.91, 0.075,
                 boxstyle='round,pad=0.008,rounding_size=0.01',
                 facecolor=PRIMARY, edgecolor='none',
                 transform=fig.transFigure, zorder=3))
    fig.text(0.075, 0.137, 'ИТОГ', fontsize=9, fontweight='bold',
             color=ACCENT, va='center', zorder=4)
    fig.text(0.135, 0.137, verdict, fontsize=11, color='white',
             va='center', zorder=4)


# ============================================================
# СТРАНИЦА 2 — СТРУКТУРА ПОСЕВОВ
# ============================================================
def _page_materials(fig, report):
    _page_shell(fig, 'Структура посевов',
                'Категории биоматериала и топ локализаций')

    cats = report['categories']
    mats = report['top_materials']

    # DONUT: уменьшена ширина (0.30 → 0.26)
    ax1 = fig.add_axes([0.045, 0.14, 0.26, 0.66])
    if not cats.empty:
        if len(cats) > 6:
            top = cats.head(5)
            rest = pd.Series({'прочее': int(cats.iloc[5:].sum())})
            cats_plot = pd.concat([top, rest])
        else:
            cats_plot = cats
        wedges, _, autotexts = ax1.pie(
            cats_plot.values, autopct='%1.0f%%', pctdistance=0.78,
            colors=CAT_PALETTE[:len(cats_plot)], startangle=110,
            wedgeprops=dict(width=0.42, edgecolor='white', linewidth=2.5))
        for t in autotexts:
            t.set_fontsize(9); t.set_color('white'); t.set_fontweight('bold')
        ax1.text(0, 0.08, f"{int(cats_plot.sum()):,}".replace(',', ' '),
                 ha='center', va='center', fontsize=22, fontweight='bold', color=PRIMARY)
        ax1.text(0, -0.16, 'проб', ha='center', va='center', fontsize=10, color=MUTED)
        ax1.legend(wedges, [_short(c, 20) for c in cats_plot.index],
                   loc='center', bbox_to_anchor=(0.5, -0.18),
                   ncol=2, fontsize=8.5, frameon=False, handlelength=1.1,
                   handleheight=1.1, columnspacing=1.2)
    ax1.set_title('Категории материала', fontsize=11, fontweight='bold',
                  color=PRIMARY, pad=14)

    # БАРЫ: сдвинуты правее (0.42 → 0.48), ширина уменьшена (0.545 → 0.48)
    # Зазор между donut (правый край 0.305) и барами (левый край 0.48) = 0.175
    ax2 = fig.add_axes([0.48, 0.14, 0.48, 0.66])
    if not mats.empty:
        y = np.arange(len(mats))
        bars = ax2.barh(y, mats.values, color=PRIMARY, height=0.62, alpha=0.92)
        ax2.set_yticks(y)
        ax2.set_yticklabels([_short(m, 28) for m in mats.index], fontsize=9)
        ax2.invert_yaxis()
        for b, v in zip(bars, mats.values):
            ax2.text(b.get_width() + mats.values.max() * 0.012,
                     b.get_y() + b.get_height() / 2,
                     str(int(v)), va='center', fontsize=8.5,
                     color=MUTED, fontweight='bold')
        ax2.set_xlim(0, mats.values.max() * 1.14)
    _clean_axes(ax2, grid_axis='x')
    ax2.set_title('Топ-10 локализаций', fontsize=11, fontweight='bold',
                  color=PRIMARY, pad=14)


# ============================================================
# СТРАНИЦА 3 — МИКРООРГАНИЗМЫ
# ============================================================
def _page_organisms(fig, report):
    _page_shell(fig, 'Выделенные микроорганизмы',
                'Топ-10 по частоте выделения из посевов с ростом')

    orgs = report['top_organisms']
    # УВЕЛИЧЕН left: 0.09 → 0.22 (место для длинных названий)
    # УМЕНЬШЕН width: 0.87 → 0.74 (правый край остаётся на 0.96)
    ax = fig.add_axes([0.22, 0.14, 0.74, 0.68])
    if not orgs.empty:
        y = np.arange(len(orgs))
        cols = [CAT_PALETTE[i % len(CAT_PALETTE)] for i in range(len(orgs))]
        bars = ax.barh(y, orgs.values, color=cols, height=0.66, alpha=0.92)
        ax.set_yticks(y)
        # УВЕЛИЧЕН лимит обрезки: 34 → 42 символа
        ax.set_yticklabels([_short(o, 42) for o in orgs.index], fontsize=10)
        ax.invert_yaxis()
        total = int(orgs.sum())
        for b, v in zip(bars, orgs.values):
            ax.text(b.get_width() + orgs.values.max() * 0.012,
                    b.get_y() + b.get_height() / 2,
                    f"{int(v)}  ({_pct(v, total)}%)",
                    va='center', fontsize=9, color=INK, fontweight='bold')
        ax.set_xlim(0, orgs.values.max() * 1.22)
    _clean_axes(ax, grid_axis='x')
    ax.set_xlabel('Число выделений', fontsize=9, color=MUTED, labelpad=8)


# ============================================================
# СТРАНИЦА 4 — АНТИБИОТИКИ: ХУДШИЕ / ЛУЧШИЕ
# ============================================================
def _page_antibiotics(fig, report):
    _page_shell(fig, 'Антибиотикочувствительность',
                'Доля штаммов, не устойчивых к препарату: (S + I) / (S + I + R) × 100 · порог n ≥ 5')

    worst = report['ab_worst']; best = report['ab_best']

    # ХУДШИЕ: left 0.055 → 0.22, width 0.42 → 0.34
    ax1 = fig.add_axes([0.22, 0.14, 0.34, 0.68])
    if not worst.empty:
        y = np.arange(len(worst))
        for yy, (v, n) in enumerate(zip(worst['S%'].values, worst['n'].values)):
            fg, _ = _s_heat(v)
            ax1.barh(y[yy], v, color=fg, height=0.62,
                     edgecolor='white', linewidth=0.8)
            ax1.text(v + 1.5, y[yy], f"{v}%  ·  n={int(n)}",
                     va='center', fontsize=8.5, color=INK)
        ax1.set_yticks(y)
        # УВЕЛИЧЕН лимит: 22 → 28 символов
        ax1.set_yticklabels([_short(a, 28) for a in worst['antibiotic']], fontsize=9)
        ax1.invert_yaxis()
        ax1.axvline(50, color=DANGER, linestyle=(0, (4, 3)), linewidth=1.2, alpha=0.7)
        ax1.text(50, -0.7, 'порог 50%', fontsize=7.5, color=DANGER, ha='center')
        ax1.set_xlim(0, 118)
    _clean_axes(ax1, grid_axis='x')
    ax1.set_title('Зона риска — наименьшая чувствительность',
                  fontsize=11, fontweight='bold', color=DANGER, pad=12, loc='left')

    # ЛУЧШИЕ: сдвинут правее (0.545 → 0.60), width 0.42 → 0.36
    ax2 = fig.add_axes([0.60, 0.14, 0.36, 0.68])
    if not best.empty:
        y = np.arange(len(best))
        for yy, (v, n) in enumerate(zip(best['S%'].values, best['n'].values)):
            fg, _ = _s_heat(v)
            ax2.barh(y[yy], v, color=fg, height=0.62,
                     edgecolor='white', linewidth=0.8)
            ax2.text(v + 1.5, y[yy], f"{v}%  ·  n={int(n)}",
                     va='center', fontsize=8.5, color=INK)
        ax2.set_yticks(y)
        ax2.set_yticklabels([_short(a, 28) for a in best['antibiotic']], fontsize=9)
        ax2.invert_yaxis()
        ax2.axvline(80, color=ACCENT_DK, linestyle=(0, (4, 3)), linewidth=1.2, alpha=0.7)
        ax2.text(80, -0.7, 'цель 80%', fontsize=7.5, color=ACCENT_DK, ha='center')
        ax2.set_xlim(0, 118)
    _clean_axes(ax2, grid_axis='x')
    ax2.set_title('Опора терапии — наибольшая чувствительность',
                  fontsize=11, fontweight='bold', color=ACCENT_DK, pad=12, loc='left')


# ============================================================
# СТРАНИЦА 5 — РЕЗИСТЕНТНЫЕ МИКРООРГАНИЗМЫ
# ============================================================
def _page_org_resistance(fig, report):
    _page_shell(fig, 'Резистентность по микроорганизмам',
                'Средняя доля «не устойчивых» штаммов по всем испытанным антибиотикам · порог n ≥ 10')

    worst = report['org_worst']
    # УВЕЛИЧЕН left: 0.10 → 0.22, width: 0.86 → 0.74
    ax = fig.add_axes([0.22, 0.14, 0.74, 0.68])
    if not worst.empty:
        y = np.arange(len(worst))
        for yy, (v, n) in enumerate(zip(worst['S%'].values, worst['n'].values)):
            fg, _ = _s_heat(v)
            ax.barh(y[yy], v, color=fg, height=0.62,
                    edgecolor='white', linewidth=0.8)
            ax.text(v + 1.2, y[yy], f"{v}%  ·  n={int(n)}",
                    va='center', fontsize=9, color=INK, fontweight='bold')
        ax.set_yticks(y)
        # УВЕЛИЧЕН лимит: 32 → 42 символа
        ax.set_yticklabels([_short(o, 42) for o in worst['organism']], fontsize=10)
        ax.invert_yaxis()
        ax.axvline(50, color=DANGER, linestyle=(0, (4, 3)), linewidth=1.2, alpha=0.7)
        ax.axvline(80, color=ACCENT_DK, linestyle=(0, (4, 3)), linewidth=1.2, alpha=0.7)
        ax.text(50, len(worst) - 0.2, 'критично', fontsize=8, color=DANGER, ha='center')
        ax.text(80, len(worst) - 0.2, 'приемлемо', fontsize=8, color=ACCENT_DK, ha='center')
        ax.set_xlim(0, 112)
    _clean_axes(ax, grid_axis='x')
    ax.set_xlabel('S%, доля «не устойчивых»', fontsize=9, color=MUTED, labelpad=8)


# ============================================================
# СТРАНИЦА 6 — ДИНАМИКА
# ============================================================
def _page_trend(fig, report):
    _page_shell(fig, 'Динамика показателей',
                'Помесячно: доля положительных посевов и средняя чувствительность')

    monthly = report['monthly']
    if monthly.empty or len(monthly) < 2:
        ax = fig.add_axes([0.1, 0.2, 0.8, 0.5])
        ax.axis('off')
        ax.text(0.5, 0.5, 'Недостаточно данных для построения тренда',
                ha='center', va='center', fontsize=12, color=MUTED)
        return

    ax1 = fig.add_axes([0.065, 0.16, 0.83, 0.64])
    x = np.arange(len(monthly))
    labels = [str(v) for v in monthly['ym_str'].values]

    bars = ax1.bar(x, monthly['pct_pos'].values, color=PRIMARY,
                   width=0.55, alpha=0.88, label='Доля положительных посевов, %')
    ax2 = ax1.twinx()
    # ИСПРАВЛЕНО: ffill().bfill() вместо fillna(method=...)
    s_vals = pd.Series(monthly['S%'].values).ffill().bfill().values
    ax2.plot(x, s_vals, color=ACCENT_DK, linewidth=2.4, marker='o',
             markersize=6, markerfacecolor='white', markeredgecolor=ACCENT_DK,
             markeredgewidth=1.8, label='S%, средняя чувствительность', zorder=5)

    ax1.set_xticks(x); ax1.set_xticklabels(labels, rotation=0, fontsize=8.5)
    ax1.set_ylabel('% положительных', fontsize=9, color=PRIMARY)
    ax2.set_ylabel('S%, %', fontsize=9, color=ACCENT_DK)
    ax1.set_ylim(0, max(float(monthly['pct_pos'].max()) * 1.35, 10))
    ax2.set_ylim(0, 100)
    ax1.tick_params(axis='y', labelcolor=PRIMARY)
    ax2.tick_params(axis='y', labelcolor=ACCENT_DK, length=0, labelsize=8.5)

    for side in ('top', 'right'):
        ax1.spines[side].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax1.spines['left'].set_color(HAIRLINE); ax1.spines['bottom'].set_color(HAIRLINE)
    ax2.spines['right'].set_color(ACCENT_DK)
    ax1.grid(axis='y', color=HAIRLINE, linestyle='-', linewidth=0.7)
    ax1.set_axisbelow(True)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc='upper left', fontsize=9,
               frameon=True, facecolor='white', edgecolor=HAIRLINE)


# ============================================================
# СТРАНИЦА 7 — КЛИНИКИ ИЛИ ВЫВОДЫ
# ============================================================
def _page_clinics(fig, report):
    cl = report['clinics']
    if cl.empty or len(cl) < 2:
        _page_conclusions(fig, report)
        return

    _page_shell(fig, 'Сравнение клиник',
                'Средняя чувствительность (S%) по клиникам · порог n ≥ 10')

    ax = fig.add_axes([0.10, 0.16, 0.86, 0.64])
    y = np.arange(len(cl))
    for yy, (v, n) in enumerate(zip(cl['S%'].values, cl['n'].values)):
        fg, _ = _s_heat(v)
        ax.barh(y[yy], v, color=fg, height=0.62,
                edgecolor='white', linewidth=0.8)
        ax.text(v + 1.2, y[yy], f"{v}%  ·  n={int(n)}",
                va='center', fontsize=9, color=INK, fontweight='bold')
    ax.set_yticks(y)
    ax.set_yticklabels([str(c) for c in cl['clinic']], fontsize=10)
    ax.invert_yaxis()
    ax.axvline(80, color=ACCENT_DK, linestyle=(0, (4, 3)), linewidth=1.2, alpha=0.7)
    ax.axvline(50, color=DANGER, linestyle=(0, (4, 3)), linewidth=1.2, alpha=0.7)
    ax.set_xlim(0, 112)
    _clean_axes(ax, grid_axis='x')
    ax.set_xlabel('S%, доля «не устойчивых»', fontsize=9, color=MUTED, labelpad=8)

    best, worst = cl.iloc[0], cl.iloc[-1]
    spread = round(best['S%'] - worst['S%'], 1)
    fig.patches.append(FancyBboxPatch((0.045, 0.075), 0.91, 0.055,
                 boxstyle='round,pad=0.006,rounding_size=0.01',
                 facecolor=PAPER_ALT, edgecolor=HAIRLINE, linewidth=0.8,
                 transform=fig.transFigure))
    fig.text(0.075, 0.102,
             f"Разброс между клиниками: {spread} п.п.   ·   "
             f"Лучшая: {best['clinic']} ({best['S%']}%)   ·   "
             f"Требует внимания: {worst['clinic']} ({worst['S%']}%)",
             fontsize=10, color=INK, va='center')


def _page_conclusions(fig, report):
    _page_shell(fig, 'Ключевые выводы и рекомендации',
                 'Сформированы автоматически по данным отчёта')

    bullets = _build_bullets(report)
    from matplotlib.gridspec import GridSpec
    gs = GridSpec(len(bullets), 1, figure=fig,
                  left=0.05, right=0.95, top=0.80, bottom=0.12,
                  hspace=0.30)
    kind_color = {'ok': ACCENT_DK, 'warn': WARNING, 'bad': DANGER, 'info': PRIMARY}
    kind_tag = {'ok': 'СИЛЬНО', 'warn': 'ВНИМАНИЕ', 'bad': 'РИСК', 'info': 'ФОН'}
    for i, (kind, text) in enumerate(bullets):
        ax = fig.add_subplot(gs[i, 0])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
        c = kind_color[kind]
        ax.add_patch(Rectangle((0, 0), 0.004, 1.0, facecolor=c,
                     edgecolor='none', transform=ax.transAxes))
        ax.text(0.015, 0.72, kind_tag[kind], fontsize=8, fontweight='bold',
                color=c, transform=ax.transAxes, va='center')
        ax.text(0.015, 0.32, text, fontsize=10.5, color=INK,
                transform=ax.transAxes, va='center', wrap=True)


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================
def generate_pdf_report(input_path, output_path, clinic=None, log_func=None):
    _setup_fonts()
    if log_func:
        log_func("PDF: загрузка данных…")

    _, _, data, antibiotics, ab_indices = load_data(input_path, log_func=log_func)

    if clinic and 'clinic' in data.columns:
        mask = data['clinic'].astype(str).str.strip() == str(clinic).strip()
        data = data[mask].copy()
        if data.empty:
            raise ValueError(f"Клиника «{clinic}» не найдена в файле.")

    if log_func:
        log_func(f"PDF: расчёт агрегатов ({len(data)} строк, "
                 f"{len(antibiotics)} антибиотиков)…")

    report = _compute_report_data(data, antibiotics, ab_indices)

    pages = [
        ('Сводка', _page_summary),
        ('Структура посевов', _page_materials),
        ('Микроорганизмы', _page_organisms),
        ('Антибиотики', _page_antibiotics),
        ('Резистентность микробов', _page_org_resistance),
        ('Динамика', _page_trend),
        ('Клиники / выводы', _page_clinics),
    ]
    total = len(pages)

    dirname = os.path.dirname(os.path.abspath(output_path))
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    with PdfPages(output_path) as pdf:
        for i, (name, fn) in enumerate(pages, start=1):
            fig = _new_figure()
            try:
                if log_func:
                    log_func(f"PDF: страница {i}/{total} — «{name}»")
                fn(fig, report)
            except Exception as e:
                fig.clf()
                fig.text(0.5, 0.5, f"Страница «{name}»: не удалось построить ({e})",
                         ha='center', va='center', fontsize=12, color=DANGER)
                if log_func:
                    log_func(f"PDF: предупреждение — страница «{name}»: {e}")
            _page_footer(fig, i, total, report['period'])
            pdf.savefig(fig, dpi=DPI)
            plt.close(fig)

    if log_func:
        log_func(f"PDF: отчёт сохранён → {output_path}")
    return output_path