# Academic CV — He (Herb) Huang

LaTeX academic CV (adapted from [Geoff Boeing’s template](https://github.com/gboeing/cv)).

## Edit once, three formats

| Role | File |
|------|------|
| **Edit this** (all facts, pubs, dates) | [`_cv-content.tex`](_cv-content.tex) |
| Shared layout / density by mode | [`_cv-preamble.tex`](_cv-preamble.tex) |
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

## Build locally

```bash
make            # PDFs + Word versions of all three lengths, into dist/
make pdf        # PDFs only
make docx       # Word versions only
make full       # full CV PDF only
make short
make onepage
make clean
```

Requires `pdflatex` (TeX Live / MacTeX) for the PDFs and `pandoc` for the Word
versions; neither target needs the other's toolchain. Overleaf: upload the repo
and set the root file to one of the three entry `.tex` files; keep `_cv-*.tex`
alongside them.

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
4. Downloads the public URLs and verifies that their bytes match the new build

Secrets required:

- R2 upload: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
  `R2_BUCKET`
- Cache purge: `CLOUDFLARE_ZONE_ID` and `CLOUDFLARE_API_TOKEN`. Scope the API
  token to the `huanghe.phd` zone with only the `Cache Purge` permission.

The purge clears Cloudflare's edge cache. It cannot remove a copy that a
visitor's browser has already cached locally.

## Workflow tips

1. Change a paper status or title in **`_cv-content.tex` only**.
2. Run `make` (or push to `main`) so all three lengths update together, in both formats.
3. To show/hide a section in a mode, wrap it with `\ifcvmedium` / `\ifcvextended` (see comments at the top of `_cv-content.tex`).
4. To tweak how dense short/one-page look, edit the density block in `_cv-preamble.tex`.
