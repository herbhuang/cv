# Build final artifacts into output/ and keep intermediates in .build/.
# Source of truth for content: _cv-content.tex
# Usage:
#   make            # PDFs + Word versions of all three lengths
#   make pdf        # PDFs only
#   make docx       # Word versions only (needs pandoc; no LaTeX required)
#   make full       # full CV PDF only
#   make short      # short CV PDF only
#   make onepage    # one-page CV PDF only
#   make clean-build # remove intermediates but keep final files
#   make clean      # remove generated artifacts and intermediates

LATEX  ?= pdflatex
LATEX_FLAGS = -interaction=nonstopmode -halt-on-error -file-line-error
PANDOC ?= pandoc
BUILD  = .build
OUTPUT = output
PDF_OUTPUT = $(OUTPUT)/pdf
DOCX_OUTPUT = $(OUTPUT)/docx
PDF_BUILD = $(BUILD)/pdf
DOCX_BUILD = $(BUILD)/docx

.PHONY: all pdf docx full short onepage clean-build clean pdf_dirs docx_dirs

all: pdf docx

pdf: full short onepage

pdf_dirs:
	@mkdir -p $(PDF_BUILD) $(PDF_OUTPUT)

docx_dirs:
	@mkdir -p $(DOCX_BUILD) $(DOCX_OUTPUT)

# Two-pass compile for footnotes / cross-refs
define compile_two_pass
	$(LATEX) $(LATEX_FLAGS) -output-directory=$(PDF_BUILD) -jobname=$(1) $(2)
	$(LATEX) $(LATEX_FLAGS) -output-directory=$(PDF_BUILD) -jobname=$(1) $(2)
	cp $(PDF_BUILD)/$(1).pdf $(PDF_OUTPUT)/$(1).pdf
endef

full: pdf_dirs
	$(call compile_two_pass,cv-hhuang,cv-hhuang.tex)

short: pdf_dirs
	$(call compile_two_pass,cv-hhuang.short,cv-hhuang.short.tex)

onepage: pdf_dirs
	$(call compile_two_pass,cv-hhuang.onepage,cv-hhuang-onepage.tex)

# Word export shares _cv-content.tex with the PDFs; see scripts/build-docx.sh.
docx: docx_dirs
	PANDOC=$(PANDOC) DIST=$(DOCX_BUILD) ./scripts/build-docx.sh
	cp $(DOCX_BUILD)/cv-hhuang.docx $(DOCX_OUTPUT)/cv-hhuang.docx
	cp $(DOCX_BUILD)/cv-hhuang.short.docx $(DOCX_OUTPUT)/cv-hhuang.short.docx
	cp $(DOCX_BUILD)/cv-hhuang.onepage.docx $(DOCX_OUTPUT)/cv-hhuang.onepage.docx

clean-build:
	rm -rf $(BUILD) dist
	rm -f *.aux *.log *.out *.fls *.fdb_latexmk *.synctex.gz

clean: clean-build
	rm -rf $(OUTPUT)
