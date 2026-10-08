-- Draft markers for the SCORE paper.
--
-- ::: gap ... :::  a boxed paragraph standing where final content will go (a figure, a
-- table, a result), saying what goes there and what it waits on. In LaTeX it is a framed
-- box; elsewhere the div passes through unchanged.
--
-- [text]{.todo}  marks a claim, number or step that is not measured or not
-- checked yet. It must survive into every output, so a reader of the PDF sees
-- it as plainly as a reader of the Markdown:
--   * LaTeX/PDF -> red "[TODO: text]"
--   * anything else -> "[TODO: text]" as plain text.
local LATEX_SPECIALS = {
  ['\\'] = '\\textbackslash{}', ['{'] = '\\{', ['}'] = '\\}', ['$'] = '\\$',
  ['&'] = '\\&', ['#'] = '\\#', ['%'] = '\\%', ['_'] = '\\_',
  ['^'] = '\\textasciicircum{}', ['~'] = '\\textasciitilde{}',
}

local function latex_escape(text)
  return (text:gsub('[\\{}$&#%%_^~]', LATEX_SPECIALS))
end

function Span(el)
  if not el.classes:includes('todo') then
    return nil
  end
  local text = pandoc.utils.stringify(el)
  if FORMAT:match('latex') then
    return pandoc.RawInline('latex', '\\textcolor{red}{[TODO: ' .. latex_escape(text) .. ']}')
  end
  return pandoc.Str('[TODO: ' .. text .. ']')
end

function Div(el)
  if not el.classes:includes('gap') or not FORMAT:match('latex') then
    return nil
  end
  local blocks = {pandoc.RawBlock('latex',
    '\\begin{center}\\fbox{\\begin{minipage}{0.94\\linewidth}\\setlength{\\parskip}{4pt}\\small')}
  for _, block in ipairs(el.content) do
    table.insert(blocks, block)
  end
  table.insert(blocks, pandoc.RawBlock('latex', '\\end{minipage}}\\end{center}'))
  return blocks
end
