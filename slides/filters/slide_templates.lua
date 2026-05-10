local function read_text_file(path)
  local f = io.open(path, "r")
  if not f then
    return ""
  end
  local content = f:read("*a")
  f:close()
  return content
end

local function md_to_html(markdown_text)
  if markdown_text == nil or markdown_text == "" then
    return ""
  end
  local doc = pandoc.read(markdown_text, "markdown")
  return pandoc.write(doc, "html")
end

local function blocks_to_html(blocks)
  if blocks == nil then
    return ""
  end
  return pandoc.write(pandoc.Pandoc(blocks), "html")
end

local function substitute(template, values)
  local output = template
  for key, value in pairs(values) do
    local safe_value = tostring(value or ""):gsub("%%", "%%%%")
    output = output:gsub("{{" .. key .. "}}", safe_value)
  end
  output = output:gsub("{{[%w_]+}}", "")
  return output
end

local function bool_attr(value)
  if not value then
    return false
  end
  local v = string.lower(value)
  return v == "1" or v == "true" or v == "yes" or v == "sim"
end

local function build_extra_images(attrs)
  local html = ""
  for i = 2, 3 do
    local img = attrs["img" .. i]
    if img and img ~= "" then
      local alt = attrs["alt" .. i] or ""
      local caption = attrs["caption" .. i] or ""
      html = html
        .. "<figure class=\"fragment\">\n"
        .. "  <img src=\"" .. img .. "\" alt=\"" .. alt .. "\" style=\"width: 92%;\" />\n"
        .. "  <figcaption>" .. caption .. "</figcaption>\n"
        .. "</figure>\n"
    end
  end
  return html
end

local function load_template(name)
  local path = "slides/templates/" .. name
  return read_text_file(path)
end

function Div(el)
  if el.classes:includes("tpl-divisor") then
    local template = load_template("tpl-divisor.html")
    local html = substitute(template, {
      title = el.attributes.title or "",
      subtitle = el.attributes.subtitle or "",
      text = el.attributes.text or ""
    })
    return { pandoc.RawBlock("html", html) }
  end

  if el.classes:includes("tpl-texto") then
    local template = load_template("tpl-texto.html")
    local html = substitute(template, {
      title = el.attributes.title or "",
      subtitle = el.attributes.subtitle or "",
      body_html = blocks_to_html(el.content)
    })
    return { pandoc.RawBlock("html", html) }
  end

  if el.classes:includes("tpl-texto-imagem") then
    local template = load_template("tpl-texto-imagem.html")
    local html = substitute(template, {
      title = el.attributes.title or "",
      img = el.attributes.img or "",
      alt = el.attributes.alt or "",
      caption = el.attributes.caption or "",
      body_html = blocks_to_html(el.content)
    })
    return { pandoc.RawBlock("html", html) }
  end

  if el.classes:includes("tpl-imagem-ampla") then
    local template = load_template("tpl-imagem-ampla.html")
    local html = substitute(template, {
      title = el.attributes.title or "",
      img = el.attributes.img or "",
      alt = el.attributes.alt or "",
      caption = el.attributes.caption or "",
      extra_images_html = build_extra_images(el.attributes)
    })
    return { pandoc.RawBlock("html", html) }
  end

  if el.classes:includes("tpl-texto-tabela") then
    local template = load_template("tpl-texto-tabela.html")
    local table_html = ""

    if el.attributes.table_file and el.attributes.table_file ~= "" then
      table_html = md_to_html(read_text_file(el.attributes.table_file))
    elseif el.attributes.table_md and el.attributes.table_md ~= "" then
      local table_md = el.attributes.table_md:gsub("\\n", "\n")
      table_html = md_to_html(table_md)
    end

    local html = substitute(template, {
      title = el.attributes.title or "",
      caption = el.attributes.caption or "",
      body_html = blocks_to_html(el.content),
      table_html = table_html
    })
    return { pandoc.RawBlock("html", html) }
  end

  if el.classes:includes("tpl-tabela-ampla") then
    local template = load_template("tpl-tabela-ampla.html")
    local table_html = ""

    if el.attributes.table_file and el.attributes.table_file ~= "" then
      table_html = md_to_html(read_text_file(el.attributes.table_file))
    elseif el.attributes.table_md and el.attributes.table_md ~= "" then
      local table_md = el.attributes.table_md:gsub("\\n", "\n")
      table_html = md_to_html(table_md)
    end

    local html = substitute(template, {
      title = el.attributes.title or "",
      caption = el.attributes.caption or "",
      table_html = table_html
    })
    return { pandoc.RawBlock("html", html) }
  end

  return nil
end
