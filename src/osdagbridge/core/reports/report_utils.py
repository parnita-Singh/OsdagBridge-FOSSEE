import re
from osdagbridge.core.reports.styles import TEXTWIDTH_CM, TABCOLSEP_PT

from osdagbridge.core.utils.common import (
    KEY_MP_GD_MEMBER_ID,
    KEY_MP_GD_SELECT_GIRDER,
    KEY_MP_GIRDER_DEPTH,
    KEY_TS_NO_OF_GIRDERS
)


def _tex(value):
    """Escape a Python value for safe LaTeX embedding."""
    s = str(value) if value is not None else ''
    if not s:
        return r''
    # Normalise non-ASCII glyphs from section designations (e.g. "∠ 100 ⅹ 100ⅹ 10")
    # that pdflatex cannot render.
    for uni, ascii_ in [('∠', 'L'), ('ⅹ', 'x'), ('×', 'x')]:
        s = s.replace(uni, ascii_)
    s = s.replace('\\', r'\textbackslash{}')
    for ch, esc in [('&', r'\&'), ('%', r'\%'), ('$', r'\$'), ('#', r'\#'),
                    ('{', r'\{'), ('}', r'\}'),          
                    ('_', r'\_\allowbreak{}'),            
                    ('~', r'\textasciitilde{}'), ('^', r'\^{}')]:
        s = s.replace(ch, esc)
    s = s.replace(':', r':\allowbreak{}')
    return s


def _render_value(source_dict, key, unit=""):
    val = source_dict.get(key)
    if val in ("", None):
        return ""
    return _tex(val) + unit


def get_girder_entries(input_dict):
    """
    Retrieve all girder labels and member IDs from backend keys.

    Usage Example:
    --------------------------
    girder_entries = get_girder_entries(bridge.input_dict)
    
    # 1. Fallback handling (if backend hasn't populated keys yet)
    if not girder_entries:
        n = int(bridge.input_dict.get(KEY_TS_NO_OF_GIRDERS, 1))
        girder_entries = [(f"Girder {i}", f"M1") for i in range(1, n + 1)]
        
    # 2. Get total number of girders safely
    n_girders = len(girder_entries)
    
    # 3. Iterate over the girders to build table rows
    for lbl, mid in girder_entries:
        # lbl will be e.g., "G1", mid will be e.g., "G1M1"
        # Access girder specific keys dynamically:
        # val = input_dict.get(f"{KEY_MP_GIRDER_DEPTH}.{lbl}.{mid}")
        pass

    Returns:
        List[Tuple[str, str]]
    """
    n = int(input_dict.get(KEY_TS_NO_OF_GIRDERS, 0))

    entries = []

    for i in range(1, n + 1):
        entries.append(
            (
                input_dict.get(f"{KEY_MP_GD_SELECT_GIRDER}.G{i}", ""),
                input_dict.get(f"{KEY_MP_GD_MEMBER_ID}.G{i}.M1", ""),
            )
        )

    return entries


def _fig_or_placeholder(path, caption, width=r'0.9\textwidth'):
    """Embed figure if path is provided (file already copied to assets), else show placeholder box.
    path is the relative path as pdflatex will see it (e.g. 'assets/plan.png').
    """
    if path:
        p = path.replace('\\', '/')
        return (r'\begin{figure}[H]' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[width=' + width + ']{' + p + '}\n'
                r'\caption*{' + caption + '}\n'
                r'\end{figure}')
    return (r'\begin{figure}[H]' + '\n'
            r'\centering' + '\n'
            r'\fbox{\parbox{0.97\textwidth}{' + '\n'
            r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
            r'}}' + '\n'
            r'\caption*{' + caption + '}\n'
            r'\end{figure}')

def _fig_embed(path, caption, width=r'\textwidth', height=None):
    """Embed a real figure when path is provided (already copied); otherwise use an fbox placeholder."""
    if path:
        p = path.replace('\\', '/')
        opts = 'width=' + width
        if height:
            opts += ',height=' + height + ',keepaspectratio'
        return (r'\begin{figure}[H]' + '\n'
                r'\vspace{-0.5em}' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[' + opts + ']{' + p + '}\n'
                r'\vspace{0.5em}' + '\n'
                r'\caption*{\small ' + caption + '}\n'
                r'\vspace{-0.5em}' + '\n'
                r'\end{figure}')
    # fbox placeholder — matches template exactly
    return (r'\noindent\fbox{\parbox{0.97\textwidth}{' + '\n'
            r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
            r'}}')



_LT = re.compile(r'(\\begin\{longtable\}(?:\[[^\]]*\])?\{(?:[^{}]|\{[^{}]*\})*\}[ \t]*\n)(.*?)(\\end\{longtable\})', re.S)
_HEAD = re.compile(
    r'\A(?P<cap>[ \t]*\\caption\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}[ \t]*(?:\\\\)?[ \t]*\n)?'
    r'(?P<h1>[ \t]*\\hline[ \t]*\n)'
    r'(?P<row>[ \t]*\\textbf\{[^\n]*\\\\(?:\[[^\]]*\])?[ \t]*\n)'
    r'(?P<h2>[ \t]*\\hline[ \t]*\n)', re.S)


def add_repeating_headers(tex: str) -> str:
    """Give every longtable with a bold header row a repeating header
    (\\endfirsthead / \\endhead) so it is reprinted after each page break."""
    def fix(m):
        begin, body, end = m.groups()
        if r'\endhead' in body or r'\endfirsthead' in body:
            return m.group(0)
        h = _HEAD.match(body)
        if not h:
            return m.group(0)
        cap = h.group('cap') or ''
        if cap and not cap.rstrip().endswith(r'\\'):
            cap = cap.rstrip() + r' \\' + '\n'
        head = h.group('h1') + h.group('row') + h.group('h2')
        new = cap + head + '\\endfirsthead\n' + head + '\\endhead\n'
        return begin + new + body[h.end():] + end
    return _LT.sub(fix, tex)


_PT_CM = 0.035146
_LT_FULL = re.compile(
    r'(\\begin\{longtable\}(?:\[[^\]]*\])?)\{((?:[^{}]|\{[^{}]*\})*)\}(.*?)(\\end\{longtable\})', re.S)
_CM = re.compile(r'(\d+(?:\.\d+)?)cm')


def _waterfill(widths, avail):
    """Cap the widest columns so the total is `avail`; narrow columns keep their width."""
    lo, hi = 0.0, max(widths)
    for _ in range(40):
        cap = (lo + hi) / 2
        if sum(min(w, cap) for w in widths) > avail:
            hi = cap
        else:
            lo = cap
    return [min(w, lo) for w in widths]


def fit_longtable_widths(tex: str, max_cm: float = TEXTWIDTH_CM - 0.1) -> str:
    """Keep every longtable inside the text block (and so centred).
    Slightly-too-wide tables: the widest columns are trimmed.
    Much-too-wide tables: also use \\small text and tighter column padding."""
    def overhead(n, tcs):
        return n * 2 * tcs * _PT_CM + (n + 1) * 0.4 * _PT_CM

    def fix(m):
        begin, spec, body, end = m.groups()
        widths = [float(w) for w in _CM.findall(spec)]
        n = len(widths)
        if n == 0 or sum(widths) + overhead(n, TABCOLSEP_PT) <= max_cm:
            return m.group(0)
        tight = (sum(widths) + overhead(n, TABCOLSEP_PT) - max_cm) / sum(widths) > 0.06
        tcs = 2.0 if tight else TABCOLSEP_PT
        new_w = iter(_waterfill(widths, max_cm - overhead(n, tcs)))
        new_spec = _CM.sub(lambda _: f"{next(new_w):.2f}cm", spec)
        out = begin + '{' + new_spec + '}' + body + end
        if tight:
            out = (r'\begingroup\setlength{\tabcolsep}{2pt}\small' + '\n'
                   + out + r'\endgroup')
        return out
    return _LT_FULL.sub(fix, tex)