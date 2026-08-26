#!/usr/bin/env bash
# Build the Word versions of the CV from the same _cv-content.tex the PDFs use.
#
#   scripts/build-docx.sh [mode ...]        # default: full short onepage
#
# _cv-content.tex -> HTML (scripts/tex2html.py) -> DOCX (pandoc). Pandoc cannot
# read the .tex directly: it expands \ent and friends into their \parshape
# internals and does not evaluate \ifcvmedium.
#
# Requires: python3, pandoc. SOURCE_DATE_EPOCH, if set, fixes the "updated"
# line so the output is reproducible.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dist="${DIST:-${root}/dist}"
pandoc_bin="${PANDOC:-pandoc}"
modes=("$@")
[[ ${#modes[@]} -eq 0 ]] && modes=(full short onepage)

for tool in python3 "${pandoc_bin}"; do
  command -v "${tool}" >/dev/null || { echo "missing: ${tool}" >&2; exit 1; }
done

mkdir -p "${dist}"

date_arg=()
if [[ -n "${SOURCE_DATE_EPOCH:-}" ]]; then
  date_arg=(--date "$(date -u -d "@${SOURCE_DATE_EPOCH}" +%F 2>/dev/null \
    || date -u -r "${SOURCE_DATE_EPOCH}" +%F)")
fi

reference="${dist}/reference.docx"
python3 "${root}/scripts/make-reference-docx.py" \
  --pandoc "${pandoc_bin}" -o "${reference}"

for mode in "${modes[@]}"; do
  case "${mode}" in
    full)    stem=cv-hhuang ;;
    short)   stem=cv-hhuang.short ;;
    onepage) stem=cv-hhuang.onepage ;;
    *) echo "unknown mode: ${mode} (full|short|onepage)" >&2; exit 2 ;;
  esac

  html="${dist}/${stem}.html"
  python3 "${root}/scripts/tex2html.py" --mode "${mode}" \
    --content "${root}/_cv-content.tex" \
    --preamble "${root}/_cv-preamble.tex" \
    "${date_arg[@]}" -o "${html}"

  # --metadata title= suppresses the Title paragraph pandoc would otherwise
  # synthesise from the HTML <title>, which duplicates the name heading.
  "${pandoc_bin}" \
    --from html --to docx \
    --metadata title= \
    --lua-filter "${root}/scripts/pagebreak.lua" \
    --reference-doc "${reference}" \
    --output "${dist}/${stem}.docx" \
    "${html}"

  echo "built ${dist}/${stem}.docx"
done
