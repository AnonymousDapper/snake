# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#
# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#

__all__ = ("LATEX_HEADER", "Program")

import shutil
from enum import Enum
from pathlib import Path

LATEX_HEADER = r"""
\\documentclass{article}
\\footnote{\\LaTeX header did not load}
"""

try:
    with Path("cogs/utils/tex/header.tex").resolve().open("r") as f:
        LATEX_HEADER = f.read()

except:
    pass

PDFLATEX_PATH = shutil.which("pdflatex") or ""
CONVERT_PATH = shutil.which("convert") or ""
TIMEOUT_PATH = shutil.which("timeout") or ""
MKDIR_PATH = shutil.which("mkdir") or ""
SH_PATH = shutil.which("sh") or ""
RM_PATH = shutil.which("rm") or ""


class Program(Enum):
    PdfLatex = Path(PDFLATEX_PATH).resolve()
    Convert = Path(CONVERT_PATH).resolve()
    Timeout = Path(TIMEOUT_PATH).resolve()
    MakeDir = Path(MKDIR_PATH).resolve()
    Sh = Path(SH_PATH).resolve()
    Rm = Path(RM_PATH).resolve()
