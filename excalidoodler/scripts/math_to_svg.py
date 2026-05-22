#!/usr/bin/env python3
"""Render one LaTeX expression to a tight-bounding-box SVG (glyphs as paths).

Pipeline: a minimal `standalone` LaTeX document -> `latex` -> DVI ->
`dvisvgm --no-fonts --exact-bbox` -> SVG. The `--no-fonts` flag traces glyphs to
vector paths so the SVG renders anywhere without font support — which is exactly
what is needed to drop typeset math onto an Excalidraw canvas that cannot itself
render LaTeX.

Usage:
    python math_to_svg.py "<latex>" <out.svg> [--color RRGGBB] [--preamble "\\usepackage{...}"]

Examples:
    python math_to_svg.py '$N = (N_1, N_2)$' expr-N.svg
    python math_to_svg.py '$Z$' label-Z.svg --color 2563EB

Requires a TeX distribution providing `latex` and `dvisvgm` (TeX Live ships both).
"""
import argparse, os, shutil, subprocess, sys, tempfile

TEMPLATE = r"""\documentclass[border=1pt]{standalone}
\usepackage{amsmath,amssymb,xcolor}
%(preamble)s
\begin{document}
%(color)s%(body)s
\end{document}
"""

def render(latex: str, out_svg: str, color: str | None = None, preamble: str = "") -> str:
    for tool in ("latex", "dvisvgm"):
        if shutil.which(tool) is None:
            sys.exit(f"error: required tool '{tool}' not found on PATH (install TeX Live).")
    color_cmd = ""
    if color:
        color_cmd = "\\definecolor{c}{HTML}{%s}\\color{c}" % color.lstrip("#").upper()
    tex = TEMPLATE % {"preamble": preamble, "color": color_cmd, "body": latex}
    out_svg = os.path.abspath(out_svg)
    with tempfile.TemporaryDirectory() as d:
        texf = os.path.join(d, "eq.tex")
        with open(texf, "w") as f:
            f.write(tex)
        r = subprocess.run(["latex", "-interaction=nonstopmode", "-halt-on-error", "eq.tex"],
                           cwd=d, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(os.path.join(d, "eq.dvi")):
            sys.exit("error: LaTeX compilation failed:\n" + r.stdout[-1500:])
        r = subprocess.run(["dvisvgm", "--no-fonts", "--exact-bbox", "eq.dvi", "-o", out_svg],
                           cwd=d, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(out_svg):
            sys.exit("error: dvisvgm failed:\n" + r.stderr[-1500:])
    return out_svg

def main():
    ap = argparse.ArgumentParser(description="Render a LaTeX expression to a tight SVG.")
    ap.add_argument("latex", help="LaTeX expression, e.g. '$N=(N_1,N_2)$'")
    ap.add_argument("out", help="output .svg path")
    ap.add_argument("--color", default=None, help="hex color for the math, e.g. 2563EB")
    ap.add_argument("--preamble", default="", help="extra LaTeX preamble lines")
    a = ap.parse_args()
    path = render(a.latex, a.out, a.color, a.preamble)
    print(f"wrote {path}")

if __name__ == "__main__":
    main()
