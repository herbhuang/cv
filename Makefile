# Build all CV variants into dist/ (source of truth for content: _cv-content.tex)
# Usage:
#   make            # build full, short, onepage PDFs
#   make full       # full CV only
#   make short      # short CV only
#   make onepage    # one-page CV only
#   make clean      # remove aux files and dist/

LATEX  ?= pdflatex
LATEX_FLAGS = -interaction=nonstopmode -halt-on-error -file-line-error
DIST   = dist

.PHONY: all full short onepage clean dirs

all: full short onepage

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

clean:
	rm -rf $(DIST)
	rm -f *.aux *.log *.out *.fls *.fdb_latexmk *.synctex.gz
