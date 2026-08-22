-- <div class="page-break"></div> in the HTML intermediate becomes a real Word
-- page break. Pandoc has no portable page-break element, so it has to be
-- emitted as raw OpenXML.
function Div (el)
  if el.classes:includes('page-break') then
    return pandoc.RawBlock('openxml',
      '<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
  end
end
