"""Single source of truth for report styling.

Every page-geometry, table-layout and colour constant used by the PyLaTeX
report lives here, so the look of the whole report can be changed in one place.
The chapter files and report_generator.py import from this module.
"""

# ---- page geometry -------------------------------------------------------
FONT_SIZE = "12pt"
PAGE_MARGIN_IN = 1.0                                  # all four margins
PAGE_GEOMETRY = f"a4paper, margin={PAGE_MARGIN_IN:g}in"
PAGE_WIDTH_CM = 21.0                                  # A4
TEXTWIDTH_CM = round(PAGE_WIDTH_CM - 2 * 2.54 * PAGE_MARGIN_IN, 2)   # usable width

# ---- table layout --------------------------------------------------------
TABCOLSEP_PT = 6.0                                    # column padding
TABCOLSEP = f"{TABCOLSEP_PT:g}pt"
ARRAY_STRETCH = "1.12"                                # row height factor

# ---- colours / status text ----------------------------------------------
OSDAG_GREEN = "91B014"                                # header / footer rules
PASS_TEX = r"\textcolor{black}{PASS}"
FAIL_TEX = r"\textcolor{red}{FAIL}"