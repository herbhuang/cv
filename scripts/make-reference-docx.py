#!/usr/bin/env python3
"""Build the Word reference document the DOCX export is styled from.

    make-reference-docx.py -o dist/reference.docx

Starts from `pandoc --print-default-data-file reference.docx` and replaces the
handful of styles the CV uses, so the Word output echoes the PDF: EB Garamond
body text, Alegreya Sans headings, tight leading, ruled section headings,
borderless layout tables and black hyperlinks. Generated at build time rather
than committed, so there is no binary in the repo to drift out of sync with
pandoc.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

BODY_FONT = "EB Garamond"
HEADING_FONT = "Alegreya Sans"
HEADING_FONTS = (f'<w:rFonts w:ascii="{HEADING_FONT}" w:hAnsi="{HEADING_FONT}" '
                 f'w:cs="{HEADING_FONT}"/>')

STYLES: dict[str, str] = {
    # body ------------------------------------------------------------------
    "Normal": """
<w:style w:type="paragraph" w:default="1" w:styleId="Normal">
  <w:name w:val="Normal"/>
  <w:pPr><w:spacing w:before="0" w:after="60" w:line="240" w:lineRule="auto"/></w:pPr>
</w:style>""",
    "BodyText": """
<w:style w:type="paragraph" w:styleId="BodyText">
  <w:name w:val="Body Text"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:spacing w:before="0" w:after="60"/></w:pPr>
</w:style>""",
    "FirstParagraph": """
<w:style w:type="paragraph" w:styleId="FirstParagraph">
  <w:name w:val="First Paragraph"/><w:basedOn w:val="BodyText"/>
</w:style>""",
    "Compact": """
<w:style w:type="paragraph" w:styleId="Compact">
  <w:name w:val="Compact"/><w:basedOn w:val="BodyText"/>
  <w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>
</w:style>""",
    # headings --------------------------------------------------------------
    # h1 is the name.
    "Heading1": f"""
<w:style w:type="paragraph" w:styleId="Heading1">
  <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="160"/>
    <w:outlineLvl w:val="0"/></w:pPr>
  <w:rPr>{HEADING_FONTS}<w:b/><w:sz w:val="34"/><w:szCs w:val="34"/></w:rPr>
</w:style>""",
    # h2 is a CV section: caps, tracked, with the rule underneath.
    "Heading2": f"""
<w:style w:type="paragraph" w:styleId="Heading2">
  <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:keepNext/><w:spacing w:before="280" w:after="80"/>
    <w:pBdr><w:bottom w:val="single" w:sz="4" w:space="2" w:color="auto"/></w:pBdr>
    <w:outlineLvl w:val="1"/></w:pPr>
  <w:rPr>{HEADING_FONTS}<w:b/><w:caps/><w:spacing w:val="14"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr>
</w:style>""",
    "Heading3": f"""
<w:style w:type="paragraph" w:styleId="Heading3">
  <w:name w:val="heading 3"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:keepNext/><w:spacing w:before="140" w:after="50"/>
    <w:outlineLvl w:val="2"/></w:pPr>
  <w:rPr>{HEADING_FONTS}<w:b/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr>
</w:style>""",
    "Heading4": f"""
<w:style w:type="paragraph" w:styleId="Heading4">
  <w:name w:val="heading 4"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:keepNext/><w:spacing w:before="100" w:after="30"/>
    <w:outlineLvl w:val="3"/></w:pPr>
  <w:rPr>{HEADING_FONTS}<w:i/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr>
</w:style>""",
    # styles tex2html.py targets by custom-style ----------------------------
    # Entry mirrors the PDF's \\cvtabw hang: wrapped lines line up half an inch
    # in, so a multi-line entry reads as one block instead of a wall of text.
    "Entry": """
<w:style w:type="paragraph" w:styleId="Entry">
  <w:name w:val="Entry"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:ind w:left="720" w:hanging="720"/>
    <w:spacing w:before="0" w:after="60"/></w:pPr>
</w:style>""",
    # the author-mark key under the Publications heading
    "Legend": """
<w:style w:type="paragraph" w:styleId="Legend">
  <w:name w:val="Legend"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:spacing w:before="0" w:after="100"/></w:pPr>
  <w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>
</w:style>""",
    # the "updated <month year>" line
    "Centered": """
<w:style w:type="paragraph" w:styleId="Centered">
  <w:name w:val="Centered"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:jc w:val="center"/><w:spacing w:before="280" w:after="60"/></w:pPr>
</w:style>""",
    # layout tables carry the date column; they must not look like tables -----
    "Table": """
<w:style w:type="table" w:styleId="Table">
  <w:name w:val="Table"/>
  <w:tblPr><w:tblCellMar>
    <w:top w:w="0" w:type="dxa"/><w:left w:w="0" w:type="dxa"/>
    <w:bottom w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/>
  </w:tblCellMar></w:tblPr>
</w:style>""",
    # the PDF prints links in black; so should the Word file ------------------
    "Hyperlink": """
<w:style w:type="character" w:styleId="Hyperlink">
  <w:name w:val="Hyperlink"/>
  <w:rPr><w:color w:val="auto"/><w:u w:val="none"/></w:rPr>
</w:style>""",
}

DOC_DEFAULTS = f"""<w:docDefaults>
  <w:rPrDefault><w:rPr>
    <w:rFonts w:ascii="{BODY_FONT}" w:hAnsi="{BODY_FONT}" w:cs="{BODY_FONT}"
              w:eastAsiaTheme="minorEastAsia"/>
    <w:sz w:val="21"/><w:szCs w:val="21"/>
    <w:lang w:val="en-US" w:eastAsia="zh-CN" w:bidi="ar-SA"/>
  </w:rPr></w:rPrDefault>
  <w:pPrDefault><w:pPr>
    <w:spacing w:before="0" w:after="60" w:line="240" w:lineRule="auto"/>
  </w:pPr></w:pPrDefault>
</w:docDefaults>"""


def compact(xml: str) -> str:
    return re.sub(r">\s+<", "><", xml.strip())


def patch_styles(xml: str) -> str:
    xml = re.sub(r"<w:docDefaults>.*?</w:docDefaults>", compact(DOC_DEFAULTS),
                 xml, count=1, flags=re.S)
    for style_id, block in STYLES.items():
        pattern = re.compile(
            rf'<w:style\b[^>]*w:styleId="{style_id}".*?</w:style>', re.S)
        if pattern.search(xml):
            xml = pattern.sub(compact(block), xml, count=1)
        else:
            xml = xml.replace("</w:styles>", compact(block) + "</w:styles>")
    return xml


def patch_sectpr(xml: str) -> str:
    """Letter paper, 1in margins -- pandoc's default reference is A4-ish."""
    sect = ('<w:pgSz w:w="12240" w:h="15840"/>'
            '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"'
            ' w:header="720" w:footer="720" w:gutter="0"/>')
    if "<w:sectPr" not in xml:
        return xml
    return re.sub(r"(<w:sectPr\b[^>]*>).*?(</w:sectPr>)",
                  lambda m: m.group(1) + sect + m.group(2), xml,
                  count=1, flags=re.S)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--pandoc", default="pandoc")
    args = ap.parse_args()

    if shutil.which(args.pandoc) is None:
        print(f"make-reference-docx: {args.pandoc} not found on PATH",
              file=sys.stderr)
        return 1

    base = subprocess.run(
        [args.pandoc, "--print-default-data-file", "reference.docx"],
        check=True, capture_output=True).stdout

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "base.docx"
        src.write_bytes(base)
        with zipfile.ZipFile(src) as zin, \
             zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/styles.xml":
                    data = patch_styles(data.decode("utf-8")).encode("utf-8")
                elif item.filename == "word/document.xml":
                    data = patch_sectpr(data.decode("utf-8")).encode("utf-8")
                zout.writestr(item, data)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
