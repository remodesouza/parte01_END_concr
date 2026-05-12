local MEDIA_BASES = { "img", "alt", "caption" }

local function includes_class(classes, class_name)
  for _, value in ipairs(classes) do
    if value == class_name then
      return true
    end
  end
  return false
end

local function is_carousel_template(el)
  return includes_class(el.classes, "tpl-text-carousel")
    or includes_class(el.classes, "tpl-wide-image")
end

local function media_base_for(key)
  for _, base in ipairs(MEDIA_BASES) do
    if key == base or key:match("^" .. base .. "[%w_-]+$") then
      return base
    end
  end
  return nil
end

local function indexed_key(base, index)
  if index == 1 then
    return base
  end
  return base .. tostring(index)
end

function Div(el)
  if not is_carousel_template(el) then
    return nil
  end

  local counts = {
    img = 0,
    alt = 0,
    caption = 0,
  }
  local normalized = {}

  for _, entry in ipairs(el.attributes) do
    local key = entry[1]
    local value = entry[2]
    local base = media_base_for(key)
    if base then
      counts[base] = counts[base] + 1
      normalized[indexed_key(base, counts[base])] = value
    else
      normalized[key] = value
    end
  end

  el.attributes = normalized
  return el
end