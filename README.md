# Academic CV — He (Herb) Huang

LaTeX academic CV (adapted from [Geoff Boeing’s template](https://github.com/gboeing/cv)).

## Edit once, three formats

| Role | File |
|------|------|
| **Edit this** (all facts, pubs, dates) | [`_cv-content.tex`](_cv-content.tex) |
| Shared typography / layout / density | [`_cv-preamble.tex`](_cv-preamble.tex) |
| Full CV entry | [`cv-hhuang.tex`](cv-hhuang.tex) (`\cvmode{full}`) |
| Short dense CV entry | [`cv-hhuang.short.tex`](cv-hhuang.short.tex) (`\cvmode{short}`) |
| One-page CV entry | [`cv-hhuang-onepage.tex`](cv-hhuang-onepage.tex) (`\cvmode{onepage}`) |

Do **not** duplicate CV text in the three entry files. They only set the mode and pull shared content.

### What each mode includes

| Section | Full | Short | One-page |
|---------|:----:|:-----:|:--------:|
| Education, research areas | ✓ | ✓ | ✓ |
| Journal articles, best paper, under review | ✓ | ✓ | ✓ |
| Awards | ✓ | ✓ | ✓ |
| Conferences, teaching (compact), membership | ✓ | ✓ | |
| Manuscripts in progress | ✓ | | |
| Full teaching + TA | ✓ | | |
| Professional development, service | ✓ | | |
| References | ✓ | | |

Density (font, margins, spacing) is controlled in `_cv-preamble.tex` from `\cvmode`.

The production typography is intentionally fixed: **EB Garamond** for the
body and the name, **Alegreya Sans** for the three heading levels. Level 1
and level 2 use Alegreya's native bold; level 3 uses its native medium italic.

## Build locally

```bash
make            # PDFs + Word versions of all three lengths
make pdf        # PDFs only
make docx       # Word versions only
make full       # full CV PDF only
make short
make onepage
make clean-build # remove intermediates but keep final files
make clean
```

Final files go to `output/pdf/` and `output/docx/`; temporary LaTeX, HTML, and
reference-document files stay in `.build/`. Requires `pdflatex` with the
`ebgaramond` and `alegreya` packages (TeX Live / MacTeX) for PDFs, and
`pandoc` for Word versions. Neither target needs the other's toolchain.
Overleaf: upload the repo and set the root file to one of the three entry
`.tex` files; keep `_cv-*.tex` alongside them. Overleaf round-trips drop the
executable bit on `scripts/`, so the Word job invokes those scripts with
`bash` rather than `./`.

### How the Word export works

`_cv-content.tex` stays the single source of truth. Pandoc cannot read it
directly -- it expands `\ent` and friends into their `\parshape` internals and
does not evaluate `\ifcvmedium` -- so the chain is:

```
_cv-content.tex --> scripts/tex2html.py --> HTML --> pandoc --> .docx
```

| File | Role |
|------|------|
| [`scripts/tex2html.py`](scripts/tex2html.py) | resolves the mode conditionals, renders the macro vocabulary to HTML |
| [`scripts/make-reference-docx.py`](scripts/make-reference-docx.py) | patches pandoc's default `reference.docx`: serif face, tight leading, ruled section headings, borderless tables, black links |
| [`scripts/pagebreak.lua`](scripts/pagebreak.lua) | turns the References page break into real OpenXML |
| [`scripts/build-docx.sh`](scripts/build-docx.sh) | runs the three modes end to end |

`tex2html.py` **fails on a macro it does not recognise** rather than dropping
it. If you add a macro to `_cv-content.tex`, the Word build breaks until you
teach it there too -- that is deliberate: silent omission from the Word CV is
worse than a red build.

The dated column becomes a two-column borderless table, so the Word file keeps
the PDF's right-aligned dates and stays editable.

## Published files and Cloudflare R2

Compiled PDFs and Word files are **not** stored in git. On every push to `main`, GitHub Actions:

1. Builds all three PDFs and all three Word versions from the shared source
2. Uploads them to Cloudflare R2:
   - `pdf/cv-hhuang.pdf`, `pdf/cv-hhuang.short.pdf`, `pdf/cv-hhuang.onepage.pdf`
   - `docx/cv-hhuang.docx`, `docx/cv-hhuang.short.docx`,
     `docx/cv-hhuang.onepage.docx`
3. Purges those six URLs from Cloudflare's edge cache so the new files are
   served immediately from `https://assets.huanghe.phd`
4. Verifies the upload by downloading each file back with a cache-busting
   query string and comparing bytes. That asks the origin, not the edge: the
   Word files are byte-reproducible (`SOURCE_DATE_EPOCH` is pinned to the
   commit), so any difference is a real one. Edge freshness is a separate
   question and is only asserted when the purge in step 3 actually ran.

Secrets required:

- R2 upload: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
  `R2_BUCKET`
- Cache purge (currently **skipped**, but wanted): `CLOUDFLARE_ZONE_ID` and
  `CLOUDFLARE_API_TOKEN`. Scope the API token to the `huanghe.phd` zone with
  only the `Cache Purge` permission. The purge step skips itself while these
  are unset so the build stays green, but the staleness it exists to prevent
  is real: measured on 2026-08-22, for a few minutes after an upload the plain
  URL served the previous object while the same path with a `?cb=` query
  string served the new one. `cf-cache-status: DYNAMIC` was reported
  throughout, so that header does not prove a response is uncached. Add both
  secrets to close the window.

The purge clears Cloudflare's edge cache. It cannot remove a copy that a
visitor's browser has already cached locally.

## Workflow tips

1. Change a paper status or title in **`_cv-content.tex` only**.
2. Run `make` (or push to `main`) so all three lengths update together, in both formats.
3. To show/hide a section in a mode, wrap it with `\ifcvmedium` / `\ifcvextended` (see comments at the top of `_cv-content.tex`).
4. To tweak how dense short/one-page look, edit the density block in `_cv-preamble.tex`.
