-- Loads ClassicUA/scripts/utils.lua outside the game so its text-code, hash and
-- match functions can be compared against the two Python copies.
--
--   lua lua_harness.lua <path to ClassicUA> code   < texts.txt
--   lua lua_harness.lua <path to ClassicUA> match  < code<TAB>candidate lines
--
-- "code" writes "code<TAB>hash" per input line; "match" writes true or false.
-- A literal \n in an input line becomes a newline.

local classicua, mode = ...
assert(classicua, 'usage: lua lua_harness.lua <path to ClassicUA> [code|match]')
mode = mode or 'code'

-- WoW globals utils.lua captures at load time. Only string.split and
-- string.trim are used by the functions under test; the rest just have to exist.
function string.split(sep, text)
    local out = {}
    for piece in (text .. sep):gmatch('(.-)' .. sep:gsub('%W', '%%%0')) do
        out[#out + 1] = piece
    end
    return table.unpack(out)
end

function string.trim(text)
    return (text:gsub('^%s+', ''):gsub('%s+$', ''))
end

C_ChatBubbles, GetMouseFoci, GetMouseFocus = {}, function() end, function() end
GetQuestID, GetQuestLogSelectedID, UnitGUID = function() end, function() end, function() end
GetBuildInfo = function() return '1.15.0', '00000', '', 11500 end

local registry = {}
local addon_table = {
    use = function(name)
        registry[name] = registry[name] or {}
        return registry[name]
    end,
}

local chunk = assert(loadfile(classicua .. '/scripts/utils.lua'))
chunk('ClassicUA', addon_table)
local utils = registry.utils

for line in io.lines() do
    if mode == 'match' then
        local code, candidate = line:match('^(.-)\t(.*)$')
        local hit = utils.match_text_code(code, { candidate })
        io.write(hit and 'true' or 'false', '\n')
    else
        local text = line:gsub('\\n', '\n')
        io.write(utils.get_text_code(text), '\t', tostring(utils.get_text_hash(text)), '\n')
    end
end
