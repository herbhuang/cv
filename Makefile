# Build all CV variants into dist/ (source of truth for content: _cv-content.tex)
# Usage:
#   make            # PDFs + Word versions of all three variants
#   make pdf        # PDFs only
#   make docx       # Word versions only (needs pandoc; no LaTeX required)
#   make full       # full CV PDF only
#   make short      # short CV PDF only
#   make onepage    # one-page CV PDF only
#   make clean      # remove aux files and dist/

LATEX  ?= pdflatex
LATEX_FLAGS = -interaction=nonstopmode -halt-on-error -file-line-error
PANDOC ?= pandoc
DIST   = dist

.PHONY: all pdf docx full short onepage clean dirs

all: pdf docx

pdf: full short onepage

dirs:
	@mkdir -p $(DIST)

# Two-pass compile for footnotes / cross-refs
define compile_two_pass
	$(LATEX) $(LATEX_FLAGS) -output-directory=$(DIST) -jobname=$(1) $(2)
	$(LATEX) $(LATEX_FLAGS) -output-directory=$(DIST) -jobname=$(1) $(2)
endef

full: dirs
	$(call compile_two_pass,cv-hhuang,cv-hhuang.tex)

short: dirs
	$(call compile_two_pass,cv-hhuang.short,cv-hhuang.short.tex)

onepage: dirs
	$(call compile_two_pass,cv-hhuang.onepage,cv-hhuang-onepage.tex)

# Word export shares _cv-content.tex with the PDFs; see scripts/build-docx.sh.
docx: dirs
	PANDOC=$(PANDOC) DIST=$(DIST) ./scripts/build-docx.sh

clean:
	rm -rf $(DIST)
	rm -f *.aux *.log *.out *.fls *.fdb_latexmk *.synctex.gz
