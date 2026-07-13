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
make            # writes dist/cv-hhuang.pdf, .short.pdf, .onepage.pdf
make full       # full only
make short
make onepage
make clean
```

Requires `pdflatex` (TeX Live / MacTeX). Overleaf: upload the repo and set the root file to one of the three entry `.tex` files; keep `_cv-*.tex` alongside them.

## PDFs and Cloudflare R2

Compiled PDFs are **not** stored in git. On every push to `main`, GitHub Actions:

1. Builds all three PDFs from the shared source
2. Uploads them to Cloudflare R2 under `pdf/`:
   - `pdf/cv-hhuang.pdf`
   - `pdf/cv-hhuang.short.pdf`
   - `pdf/cv-hhuang.onepage.pdf`

Secrets required: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.

## Workflow tips

1. Change a paper status or title in **`_cv-content.tex` only**.
2. Run `make` (or push to `main`) so all three PDFs update together.
3. To show/hide a section in a mode, wrap it with `\ifcvmedium` / `\ifcvextended` (see comments at the top of `_cv-content.tex`).
4. To tweak how dense short/one-page look, edit the density block in `_cv-preamble.tex`.
