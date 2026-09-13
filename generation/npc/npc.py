import json
import os
import re

import requests
from bs4 import BeautifulSoup

from generation.utils.utils import wowhead_get

SCRAPE_THREADS = 1
PARSE_THREADS = os.cpu_count()
CLASSIC = 'classic'
TBC = 'tbc'
WRATH = 'wrath'
CATA = 'cata'
MISTS = 'mists'
WOWHEAD_URL = 'wowhead_url'
METADATA_CACHE = 'metadata_cache'
HTML_CACHE = 'html_cache'
NPC_CACHE = 'npc_cache'
IGNORES = 'ignores'
INDEX = 'index'
METADATA_FILTERS = 'metadata_filters'
SOD = 'sod'
FORCE_DOWNLOAD = 'force_download'
RETRIEVE_QUOTES = 'retrieve_quotes'
FORCE_LOAD_NAME = 'FORCE LOAD'  # placeholder until the real name is read off the NPC page

expansion_data = {
    CLASSIC: {
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_classic_metadata_cache',
        HTML_CACHE: 'wowhead_classic_npc_html',
        NPC_CACHE: 'wowhead_classic_npc_cache',
        METADATA_FILTERS: ('13:', '5:', '11500:'),
        IGNORES: [],
        FORCE_DOWNLOAD: [],
        RETRIEVE_QUOTES: True
    },
    SOD: {
        WOWHEAD_URL: 'https://www.wowhead.com/classic',
        METADATA_CACHE: 'wowhead_sod_metadata_cache',
        HTML_CACHE: 'wowhead_sod_npc_html',
        NPC_CACHE: 'wowhead_sod_npc_cache',
        METADATA_FILTERS: ('13:', '2:', '11500:'),
        IGNORES: [],
        # SoD is retired and Wowhead's search no longer lists it completely. Sourced from the last complete harvest.
        FORCE_DOWNLOAD: [91914, 162539, 169106, 173338, 176552, 176553, 176663, 176721, 177063, 183709, 183713, 184314, 184383, 185273, 185320, 185331, 185332, 185336, 185342, 185371, 185378, 185379, 185380, 185536, 185585, 185590, 185605, 185631, 185650, 185658, 185746, 185760, 185859, 186348, 187162, 187237, 187274, 187309, 187327, 187345, 187346, 187383, 187564, 187664, 187724, 187725, 187728, 187729, 187798, 187801, 187832, 187978, 187993, 188018, 188109, 188110, 188111, 188119, 188131, 188134, 188147, 188148, 188170, 188178, 188182, 188183, 200571, 201722, 201854, 201933, 202060, 202079, 202093, 202116, 202387, 202390, 202391, 202392, 202699, 202838, 202839, 202840, 203079, 203138, 203139, 203147, 203218, 203226, 203279, 203475, 203478, 203694, 204068, 204070, 204091, 204253, 204256, 204346, 204503, 204545, 204645, 204675, 204758, 204827, 204921, 204937, 204940, 204960, 204961, 204962, 204989, 205153, 205278, 205382, 205383, 205422, 205423, 205635, 205692, 205700, 205724, 205729, 205733, 205765, 205767, 205805, 206152, 206153, 206154, 206155, 206217, 206245, 206248, 207010, 207356, 207358, 207359, 207367, 207397, 207457, 207515, 207520, 207527, 207576, 207577, 207588, 207637, 207743, 207754, 207795, 207957, 208023, 208036, 208071, 208124, 208127, 208128, 208158, 208179, 208180, 208184, 208196, 208226, 208275, 208307, 208309, 208518, 208546, 208565, 208619, 208638, 208652, 208682, 208711, 208712, 208752, 208758, 208802, 208809, 208810, 208811, 208812, 208841, 208842, 208843, 208844, 208845, 208846, 208847, 208875, 208876, 208886, 208919, 208920, 208927, 208974, 208975, 209002, 209004, 209209, 209213, 209214, 209511, 209524, 209548, 209607, 209608, 209678, 209742, 209758, 209773, 209797, 209806, 209811, 209812, 209815, 209830, 209872, 209889, 209908, 209928, 209939, 209940, 209941, 209948, 209949, 209954, 209958, 210006, 210107, 210451, 210482, 210483, 210487, 210501, 210528, 210533, 210537, 210549, 210697, 210750, 210802, 210845, 210887, 210901, 210995, 211022, 211033, 211042, 211043, 211146, 211183, 211188, 211200, 211225, 211229, 211269, 211274, 211279, 211298, 211330, 211338, 211552, 211653, 211736, 211764, 211765, 211839, 211875, 211941, 211951, 211952, 211953, 211954, 211955, 211956, 211965, 211967, 212157, 212159, 212186, 212209, 212252, 212261, 212330, 212333, 212334, 212443, 212458, 212461, 212462, 212463, 212468, 212598, 212667, 212674, 212678, 212692, 212694, 212699, 212703, 212706, 212707, 212727, 212728, 212729, 212730, 212753, 212763, 212801, 212802, 212803, 212804, 212809, 212837, 212934, 212953, 212969, 212970, 213077, 213334, 213444, 213445, 213450, 213451, 213452, 213540, 213595, 213659, 213708, 213709, 213710, 213711, 213795, 213994, 214000, 214063, 214070, 214096, 214098, 214099, 214101, 214129, 214133, 214190, 214208, 214212, 214254, 214440, 214456, 214458, 214468, 214469, 214519, 214523, 214524, 214525, 214526, 214527, 214528, 214529, 214530, 214589, 214603, 214612, 214658, 214695, 214830, 214837, 214876, 214914, 214954, 215062, 215072, 215081, 215095, 215096, 215097, 215098, 215108, 215367, 215369, 215643, 215655, 215688, 215709, 215728, 215849, 215850, 215854, 215855, 215890, 215974, 216098, 216126, 216145, 216289, 216310, 216437, 216445, 216448, 216451, 216463, 216474, 216620, 216659, 216660, 216661, 216662, 216664, 216665, 216666, 216667, 216668, 216669, 216670, 216671, 216672, 216810, 216854, 216902, 216915, 216924, 216931, 216937, 217049, 217215, 217216, 217221, 217280, 217290, 217300, 217302, 217305, 217308, 217387, 217392, 217412, 217418, 217580, 217582, 217588, 217589, 217590, 217605, 217620, 217669, 217683, 217689, 217703, 217706, 217707, 217711, 217733, 217783, 217836, 217862, 217908, 217942, 217943, 217945, 217956, 217957, 217969, 217980, 217987, 217996, 218007, 218019, 218020, 218021, 218029, 218032, 218057, 218089, 218090, 218093, 218095, 218115, 218160, 218229, 218230, 218231, 218232, 218233, 218234, 218235, 218236, 218237, 218238, 218240, 218241, 218242, 218243, 218244, 218245, 218246, 218249, 218262, 218263, 218273, 218343, 218344, 218345, 218349, 218386, 218537, 218538, 218571, 218606, 218610, 218624, 218627, 218683, 218690, 218706, 218718, 218721, 218776, 218792, 218813, 218819, 218868, 218869, 218870, 218871, 218873, 218891, 218908, 218920, 218922, 218930, 218931, 218935, 218969, 218970, 218971, 218972, 218973, 218974, 218975, 219110, 219111, 219112, 219113, 219177, 219199, 219624, 219659, 219663, 219704, 219791, 219822, 219986, 219999, 220007, 220064, 220072, 220076, 220142, 220170, 220174, 220178, 220179, 220358, 220396, 220833, 220864, 220908, 220929, 220930, 220931, 220932, 220933, 220934, 220935, 220936, 220937, 220942, 220984, 221165, 221168, 221169, 221170, 221171, 221172, 221173, 221174, 221175, 221176, 221200, 221201, 221204, 221206, 221207, 221208, 221210, 221215, 221216, 221220, 221221, 221222, 221223, 221226, 221227, 221230, 221257, 221258, 221259, 221260, 221261, 221262, 221263, 221264, 221265, 221266, 221267, 221268, 221269, 221270, 221271, 221272, 221273, 221282, 221283, 221292, 221312, 221315, 221324, 221325, 221326, 221328, 221329, 221330, 221331, 221333, 221334, 221335, 221336, 221337, 221351, 221352, 221353, 221356, 221357, 221360, 221361, 221364, 221365, 221367, 221369, 221370, 221371, 221373, 221375, 221377, 221389, 221391, 221393, 221394, 221395, 221396, 221398, 221399, 221400, 221401, 221402, 221404, 221406, 221407, 221408, 221426, 221471, 221472, 221477, 221479, 221480, 221482, 221483, 221484, 221575, 221587, 221636, 221637, 221638, 221639, 221640, 221651, 221656, 221732, 221740, 221759, 221761, 221762, 221827, 221828, 221829, 221830, 221831, 221832, 221833, 221834, 221835, 221836, 221837, 221838, 221916, 221924, 221928, 221933, 221935, 221942, 221943, 221985, 222004, 222005, 222008, 222044, 222052, 222058, 222088, 222089, 222174, 222188, 222192, 222198, 222210, 222225, 222228, 222231, 222232, 222233, 222240, 222243, 222261, 222286, 222288, 222289, 222290, 222293, 222316, 222367, 222376, 222402, 222403, 222404, 222405, 222406, 222407, 222408, 222409, 222410, 222411, 222412, 222413, 222414, 222415, 222416, 222418, 222444, 222451, 222478, 222495, 222513, 222514, 222516, 222519, 222521, 222522, 222525, 222530, 222531, 222542, 222543, 222544, 222545, 222546, 222551, 222553, 222566, 222573, 222580, 222617, 222620, 222623, 222625, 222636, 222647, 222648, 222649, 222650, 222651, 222656, 222684, 222685, 222686, 222687, 222689, 222694, 222695, 222696, 222697, 222698, 222699, 222701, 222702, 222703, 222704, 222705, 222706, 222707, 222708, 222709, 222710, 222726, 222763, 222765, 222768, 222772, 222789, 222799, 222856, 222857, 222897, 222919, 222939, 222968, 222970, 222971, 222972, 222977, 222978, 223061, 223068, 223123, 223127, 223128, 223130, 223131, 223264, 223265, 223287, 223340, 223345, 223359, 223374, 223482, 223483, 223485, 223496, 223542, 223543, 223544, 223568, 223581, 223586, 223587, 223588, 223590, 223591, 223689, 223734, 223739, 224242, 224243, 224244, 224245, 224250, 224253, 224254, 224255, 224256, 224257, 224258, 224259, 224260, 224262, 224263, 224328, 224386, 224743, 224965, 226797, 226799, 226921, 226922, 226923, 226982, 227019, 227028, 227140, 227206, 227324, 227385, 227386, 227387, 227464, 227493, 227511, 227519, 227533, 227672, 227673, 227674, 227681, 227705, 227746, 227755, 227819, 227853, 227856, 227857, 227858, 227866, 227938, 227939, 227951, 227985, 227995, 227996, 228022, 228062, 228079, 228142, 228145, 228173, 228176, 228203, 228204, 228206, 228209, 228216, 228230, 228231, 228232, 228233, 228287, 228353, 228414, 228429, 228430, 228431, 228432, 228433, 228434, 228435, 228436, 228437, 228438, 228441, 228442, 228461, 228532, 228533, 228551, 228595, 228596, 228609, 228610, 228611, 228612, 228618, 228619, 228620, 228622, 228673, 228676, 228677, 228703, 228714, 228718, 228719, 228720, 228721, 228722, 228723, 228724, 228725, 228726, 228727, 228728, 228729, 228730, 228731, 228738, 228747, 228748, 228770, 228771, 228786, 228793, 228814, 228816, 228818, 228820, 228822, 228833, 228834, 228835, 228836, 228837, 228838, 228891, 228902, 228906, 228907, 228908, 228909, 228910, 228911, 228912, 228913, 228914, 228915, 228916, 228917, 228918, 228919, 228920, 228928, 228929, 228930, 228931, 228932, 228934, 228935, 228936, 228944, 228956, 228969, 228970, 228976, 229000, 229001, 229009, 229016, 229018, 229035, 229047, 229049, 229051, 229052, 229057, 229061, 229091, 229110, 229140, 229156, 229200, 229202, 229311, 229312, 229390, 229425, 229452, 229454, 229485, 229515, 229564, 229631, 229632, 229731, 229732, 229733, 229737, 229802, 229803, 229805, 229840, 229897, 229984, 230039, 230069, 230088, 230146, 230302, 230317, 230319, 230347, 230348, 230349, 230481, 230513, 230558, 230565, 230566, 230695, 230775, 230949, 231002, 231050, 231054, 231103, 231178, 231384, 231430, 231485, 231494, 231498, 231499, 231500, 231661, 231691, 231711, 231779, 231810, 231858, 231868, 231871, 231872, 231887, 231980, 231982, 231984, 231990, 231991, 231992, 231996, 232074, 232075, 232103, 232104, 232105, 232107, 232109, 232190, 232215, 232216, 232223, 232270, 232286, 232309, 232335, 232380, 232381, 232386, 232398, 232399, 232422, 232424, 232426, 232429, 232462, 232466, 232467, 232479, 232529, 232532, 232534, 232538, 232556, 232557, 232558, 232559, 232560, 232561, 232562, 232564, 232565, 232566, 232567, 232568, 232587, 232596, 232597, 232619, 232624, 232625, 232627, 232628, 232630, 232632, 232634, 232638, 232651, 232670, 232694, 232708, 232709, 232710, 232711, 232713, 232714, 232725, 232729, 232731, 232741, 232744, 232746, 232747, 232752, 232754, 232755, 232756, 232775, 232778, 232781, 232799, 232802, 232816, 232817, 232818, 232826, 232848, 232853, 232854, 232855, 232867, 232869, 232875, 232880, 232884, 232886, 232896, 232899, 232900, 232903, 232912, 232920, 232921, 232922, 232924, 232926, 232928, 232929, 232930, 232931, 232932, 232936, 232937, 232938, 232939, 232940, 232942, 232943, 232944, 232945, 232947, 232959, 232960, 232994, 232995, 232996, 232997, 232998, 233017, 233027, 233029, 233031, 233033, 233047, 233048, 233049, 233084, 233093, 233138, 233158, 233159, 233165, 233175, 233178, 233206, 233234, 233246, 233249, 233264, 233308, 233315, 233335, 233382, 233414, 233428, 233574, 233575, 233776, 233988, 234072, 234139, 234183, 234184, 234193, 234218, 234472, 234539, 234542, 234543, 234544, 234545, 234546, 234577, 234651, 234752, 234755, 234762, 234794, 234798, 234800, 234814, 234830, 234880, 234917, 234954, 234961, 234963, 234969, 234973, 234979, 234987, 234990, 234996, 235008, 235042, 235043, 235044, 235047, 235048, 235049, 235050, 235164, 235180, 235197, 235207, 235208, 235209, 235232, 235251, 235282, 235284, 235285, 235286, 235287, 235288, 235289, 235291, 235325, 235326, 235327, 235328, 235396, 235406, 235528, 235668, 235761, 235762, 235786, 235880, 235881, 235910, 236007, 236008, 236034, 236077, 236173, 236619, 236633, 236811, 236869, 236971, 236979, 237318, 237328, 237374, 237439, 237460, 237657, 237670, 237671, 237672, 237673, 237674, 237675, 237676, 237677, 237678, 237754, 237757, 237773, 237818, 237819, 237820, 237821, 237823, 237824, 237938, 237957, 237961, 237964, 237969, 237994, 238018, 238024, 238038, 238040, 238041, 238042, 238043, 238044, 238055, 238100, 238111, 238160, 238161, 238191, 238192, 238193, 238200, 238206, 238208, 238211, 238213, 238233, 238234, 238244, 238245, 238251, 238252, 238253, 238261, 238262, 238263, 238264, 238270, 238286, 238292, 238303, 238304, 238305, 238306, 238307, 238308, 238309, 238310, 238311, 238324, 238325, 238326, 238327, 238328, 238329, 238330, 238331, 238332, 238355, 238356, 238365, 238374, 238376, 238382, 238407, 238415, 238416, 238417, 238418, 238419, 238420, 238421, 238422, 238423, 238424, 238425, 238426, 238427, 238428, 238429, 238430, 238431, 238432, 238433, 238434, 238435, 238436, 238437, 238438, 238440, 238441, 238442, 238443, 238444, 238445, 238447, 238448, 238449, 238450, 238451, 238452, 238453, 238454, 238455, 238456, 238457, 238458, 238459, 238460, 238461, 238477, 238499, 238503, 238508, 238509, 238511, 238512, 238526, 238527, 238528, 238556, 238558, 238559, 238560, 238561, 238562, 238563, 238589, 238593, 238594, 238598, 238620, 238627, 238628, 238629, 238630, 238638, 238639, 238640, 238641, 238642, 238643, 238644, 238645, 238646, 238647, 238648, 238650, 238654, 238656, 238657, 238678, 238679, 238680, 238681, 238682, 238715, 238716, 238725, 238734, 238737, 238745, 238761, 238766, 238767, 238941, 238942, 238943, 238954, 238985, 238986, 238992, 239031, 239032, 239036, 239046, 239047, 239054, 239139, 239146, 239151, 239187, 239189, 239328, 239329, 239334, 239336, 239337, 239363, 239365, 239382, 239386, 239573, 239640, 239642, 239713, 239714, 239715, 240122, 240246, 240247, 240248, 240310, 240352, 240568, 240604, 240607, 240609, 240631, 240632, 240633, 240636, 240639, 240654, 240779, 240780, 240781, 240782, 240783, 240784, 240785, 240786, 240787, 240788, 240789, 240790, 240791, 240792, 240793, 240794, 240795, 240796, 240797, 240798, 240799, 240800, 240801, 240802, 240803, 240804, 240805, 240806, 240807, 240808, 240809, 240810, 240811, 240812, 240825, 240978, 240998, 241006, 241019, 241021, 241032, 241048, 241119, 241120, 241121, 241122, 241123, 241136, 241149, 241329, 241334, 241406, 241407, 241408, 241409, 241411, 241434, 241437, 241492, 241493, 241501, 241518, 241519, 241613, 241616, 241659, 241663, 241664, 241665, 241768, 241769, 241770, 241772, 241778, 241785, 241786, 241787, 241825, 241826, 241827, 241828, 241830, 241834, 241838, 241862, 241877, 241895, 241904, 241906, 241921, 241940, 241985, 242007, 242008, 242009, 242010, 242019, 242062, 242092, 242093, 242098, 242106, 242107, 242108, 242109, 242110, 242111, 242112, 242113, 242114, 242125, 242135, 242137, 242141, 242142, 242148, 242158, 242159, 242160, 242161, 242169, 242174, 242182, 242183, 242188, 242204, 242214, 242216, 242218, 242224, 242229, 242240, 242243, 242245, 242246, 242250, 242271, 242272, 242275, 242279, 242282, 242283, 242296, 242298, 242300, 242301, 242304, 242308, 242310, 242329, 242344, 242345, 242354, 242367, 242371, 242373, 242378, 242380, 242386, 242389, 242424, 242427, 242439, 242450, 242466, 242470, 242477, 242479, 242499, 242501, 242510, 242516, 242547, 242554, 242555, 242556, 242557, 242558, 242559, 242560, 242561, 242562, 242563, 242564, 242565, 242572, 242573, 242574, 242575, 242576, 242577, 242580, 242605, 242624, 242629, 242641, 242660, 242690, 242741, 242751, 242756, 242757, 242782, 242788, 242789, 242790, 242791, 242792, 242793, 242796, 242816, 242827, 242828, 242853, 242862, 242863, 242867, 242870, 242872, 242874, 242877, 242878, 242886, 242892, 242908, 242922, 242923, 242924, 242925, 242926, 242927, 242954, 242957, 242958, 243001, 243005, 243007, 243011, 243012, 243013, 243014, 243015, 243016, 243017, 243018, 243019, 243021, 243022, 243023, 243025, 243026, 243027, 243046, 243047, 243050, 243051, 243056, 243057, 243060, 243076, 243086, 243087, 243094, 243096, 243099, 243100, 243139, 243158, 243159, 243184, 243186, 243187, 243189, 243190, 243191, 243192, 243193, 243194, 243195, 243250, 243251, 243252, 243254, 243255, 243269, 243271, 243299, 243331, 243332, 243337, 243386, 243393, 243394, 243627, 243628, 243632, 243637, 243645, 243647, 243648, 243657, 243702, 243737, 243755, 243756, 243757, 243783, 243790, 243834, 243838, 243893, 243904, 243911, 243914, 243917, 243943, 243946, 243954, 244005, 244006, 244007, 244008, 244009, 244010, 244011, 244013, 244014, 244015, 244016, 244017, 244018, 244019, 244020, 244021, 244022, 244023, 244024, 244064, 244065, 244066, 244067, 244068, 244069, 244102, 244103, 244104, 244105, 244106, 244107, 244122, 244131, 244132, 244133, 244134, 244135, 244136, 244147, 244151, 244155, 244172, 244265, 244306, 244307, 244310, 244311, 244321, 244460, 244462, 244477, 244480, 244481, 244482, 244495, 244527, 244612, 244721, 244766, 244795, 244819, 244852, 244855, 244861, 244949, 245070, 245234, 245321, 245332, 245337, 245340, 245342, 245343, 245373, 245376, 245423, 245488, 245490, 245491, 245492, 245493, 245507, 245534, 245542, 245633, 245634, 245635],
        RETRIEVE_QUOTES: True
    },
    TBC: {
        WOWHEAD_URL: 'https://www.wowhead.com/tbc',
        METADATA_CACHE: 'wowhead_tbc_metadata_cache',
        HTML_CACHE: 'wowhead_tbc_npc_html',
        NPC_CACHE: 'wowhead_tbc_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: [],
        RETRIEVE_QUOTES: True
    },
    WRATH: {
        WOWHEAD_URL: 'https://www.wowhead.com/wotlk',
        METADATA_CACHE: 'wowhead_wrath_metadata_cache',
        HTML_CACHE: 'wowhead_wrath_npc_html',
        NPC_CACHE: 'wowhead_wrath_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: [],
        RETRIEVE_QUOTES: True
    },
    CATA: {
        WOWHEAD_URL: 'https://www.wowhead.com/cata',
        METADATA_CACHE: 'wowhead_cata_metadata_cache',
        HTML_CACHE: 'wowhead_cata_npc_html',
        NPC_CACHE: 'wowhead_cata_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: [],
        RETRIEVE_QUOTES: False
    },
    MISTS: {
        WOWHEAD_URL: 'https://www.wowhead.com/mop-classic',
        METADATA_CACHE: 'wowhead_mists_metadata_cache',
        HTML_CACHE: 'wowhead_mists_npc_html',
        NPC_CACHE: 'wowhead_mists_npc_cache',
        METADATA_FILTERS: ('', '', ''),
        IGNORES: [],
        FORCE_DOWNLOAD: [],
        RETRIEVE_QUOTES: False
    }
}


# Metadata from Wowhead
class NPC_MD:
    # def __init__(self, id: int, name: str, tag: str = None, type: int = None, boss: int = None,
    #              classification: int = None, displayName: str = None, displayNames: list[str] = None,
    #              location: list[int] = None, names: list[str] = None, react: list[int] = None, expansion: str = None):
    def __init__(self, id, name, tag=None, name_ua=None, tag_ua=None, type=None, boss=None, classification=None, location=None, names=None, react=None, expansion=None):
        self.id = id
        self.name = name
        self.tag = tag
        self.name_ua = name_ua
        self.tag_ua = tag_ua
        self.type = type
        self.boss = boss
        self.classification = classification
        self.location = location
        self.names = names
        self.react = react
        self.expansion = expansion
        def get_classification(self):
            if self.classification == 0:
                return 'normal'
            elif self.classification == 1:
                return 'elite'
            elif self.classification == 2:
                return 'rare elite'
            elif self.classification == 3:
                return 'boss'
            elif self.classification == 4:
                return 'rare'

    def __str__(self):
        res = f'#{self.id}:'
        res += f' "{self.name}"'
        res += f' <{self.tag}>' if self.tag else ''
        return res

    def __eq__(self, __value):
        return self.name == __value.name and self.name_ua == __value.name_ua and self.name_ua == __value.name_ua


class NPC_Short:
    def __init__(self, id, name, tag=None):
        self.id = id
        self.name = name
        self.tag = tag


class NPC_Data:
    def __init__(self, id, expansion, name: str = None, quotes: list[str] = [], tag: str = None, name_ua: str = None):
        self.id = id
        self.expansion = expansion
        self.name = name
        self.tag = tag
        self.name_ua = name_ua
        self.quotes = quotes


def __get_wowhead_npc_search(expansion, start, end=None) -> list[NPC_MD]:
    base_url = expansion_data[expansion][WOWHEAD_URL]
    metadata_filters = expansion_data[expansion][METADATA_FILTERS]
    if end:
        url = base_url + f"/npcs?filter={metadata_filters[0]}37:37;{metadata_filters[1]}2:5;{metadata_filters[2]}{start}:{end}"
    else:
        url = base_url + f"/npcs?filter={metadata_filters[0]}37;{metadata_filters[1]}2;{metadata_filters[2]}{start}"
    r = wowhead_get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    pre_script_div = soup.find('div', id='lv-npcs')
    if not pre_script_div:
        # An empty result set still renders the NPC listview scaffolding. If even that is missing - we got an error page.
        if 'Listview/Templates/npc.js' not in r.text:
            raise Exception(f'Wowhead({expansion}) returned an unexpected page for {url}')
        return []
    script_tag = pre_script_div.next_element
    if script_tag:
        script_content = script_tag.text
        start = script_content.find('new Listview(') + 13
        start = script_content.find('"data":[', start) + 7
        end = script_content.rfind('}],"') + 2
        json_data = script_content[start:end]
        return list(map(lambda md: NPC_MD(md.get('id'), md.get('name'), md.get('tag'), None, None, md.get('type'), md.get('boss'),
                                          md.get('classification'), md.get('location'), md.get('names'), md.get('react'), expansion), json.loads(json_data)))
    else:
        return []


def __retrieve_npc_metadata_from_wowhead(expansion) -> dict[int, NPC_MD]:
    all_npcs_metadata = []
    i = 0
    while True:
        start = i * 1000
        if (i % 10 == 0):
            npcs = __get_wowhead_npc_search(expansion, start)
            if len(npcs) < 1000:
                all_npcs_metadata.extend(npcs)
                break
        npcs = __get_wowhead_npc_search(expansion, start, start + 1000)
        all_npcs_metadata.extend(npcs)
        i += 1
    return {md.id: md for md in all_npcs_metadata}



def get_wowhead_npc_metadata(expansion) -> dict[int, dict[str, NPC_MD]]:
    import pickle
    cache_file_name = expansion_data[expansion][METADATA_CACHE]
    if os.path.exists(f'cache/tmp/{cache_file_name}.pkl'):
        print(f'Loading cached Wowhead({expansion}) metadata')
        with open(f'cache/tmp/{cache_file_name}.pkl', 'rb') as f:
            wowhead_metadata = pickle.load(f)
    else:
        print(f'Retrieving Wowhead({expansion}) metadata')
        wowhead_metadata = __retrieve_npc_metadata_from_wowhead(expansion)
        os.makedirs('cache/tmp', exist_ok=True)
        with open(f'cache/tmp/{cache_file_name}.pkl', 'wb') as f:
            pickle.dump(wowhead_metadata, f)

    for ignore_id in expansion_data[expansion][IGNORES]:
        if ignore_id in wowhead_metadata:
            del wowhead_metadata[ignore_id]

    # Wowhead's search no longer lists retired content (SoD in particular), so those NPCs are pinned by ID.
    # The real name/tag is filled in from their page later, by apply_page_data_to_metadata().
    for force_id in expansion_data[expansion][FORCE_DOWNLOAD]:
        if force_id not in wowhead_metadata:
            wowhead_metadata[force_id] = NPC_MD(force_id, FORCE_LOAD_NAME, expansion=expansion)
        else:
            print(f"Warning! NPC #{id}:{expansion} forced to load, but already exists in Wowhead metadata")

    wowhead_npcs = dict()
    for key, value in wowhead_metadata.items():
        wowhead_npcs[key] = dict()
        wowhead_npcs[key][expansion] = value

    return wowhead_npcs

def load_npc_lua(path: str) -> dict[int, NPC_Short]:
    from slpp import slpp as lua
    npcs = dict()
    if not os.path.exists(path):  # an expansion with no NPC translations yet
        print(f'Warning! No entries at {path}, treating as untranslated')
        return npcs
    with open(path, 'r', encoding='utf-8') as input_file:
        lua_file = input_file.read()
        start = lua_file.find("npc = {") + 5
        decoded_npcs = lua.decode(lua_file[start:])
        for npc_id, decoded_npc in decoded_npcs.items():
            npc_name_ua = decoded_npc[0]
            if type(decoded_npc) == dict:
                npc_tag_ua = decoded_npc.get(1)
            else:
                npc_tag_ua = decoded_npc[1] if len(decoded_npc) > 1 else None
            npcs[npc_id] = NPC_Short(npc_id, npc_name_ua, npc_tag_ua)
    return npcs

def load_questie_npcs() -> dict[int, NPC_Short]:
    from slpp import slpp as lua
    npcs = dict()
    with open('input/questie_npc.lua', 'r', encoding='utf-8') as input_file:
        lua_file = input_file.read()
        decoded_npcs = lua.decode(lua_file)
        for npc_id, decoded_npc in decoded_npcs.items():
            npc_name = decoded_npc[0]
            npc_tag = None
            if len(decoded_npc) == 2:
                npc_tag = decoded_npc[1]
            npcs[npc_id] = NPC_Short(npc_id, npc_name, npc_tag)
    return npcs

# def apply_translations(wowhead_metadata: dict[int, NPC_MD]):

def save_npcs_to_db(all_npcs: dict[int, dict[str, NPC_MD]]):
    import sqlite3
    print('Saving NPCs to DB')
    conn = sqlite3.connect('cache/npcs.db')
    conn.execute('DROP TABLE IF EXISTS npcs')
    conn.execute('''CREATE TABLE npcs (
                        id INT NOT NULL,
                        expansion TEXT,
                        name TEXT,
                        tag TEXT,
                        name_ua TEXT,
                        tag_ua TEXT,
                        type TEXT,
                        boss TEXT,
                        classification TEXT,
                        location TEXT,
                        names TEXT,
                        react TEXT
                )''')
    conn.commit()
    with conn:
        for key, npcs in all_npcs.items():
            for expansion, npc in npcs.items():
                if ('TEST' in npc.name or
                        '[PH]' in npc.name or
                        'DND' in npc.name or
                        'DNT' in npc.name or
                        'UNUSED' in npc.name or
                        '<TXT>' in npc.name or
                        key in expansion_data[npc.expansion][IGNORES]):
                    continue
                npc_tag = f'<{npc.tag}>' if npc.tag else None
                npc_location = ', '.join(map(lambda x: f"'{x}'", npc.location)) if npc.location else None
                conn.execute('INSERT INTO npcs(id, expansion, name, tag, name_ua, tag_ua, type, boss, classification, location, names, react) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                            (npc.id, expansion, npc.name, npc_tag, npc.__dict__.get('name_ua'), npc.__dict__.get('tag_ua'), npc.type, npc.boss, npc.classification, npc_location, str(npc.names), str(npc.react)))


def load_npcs_from_db(db_path = 'cache/npcs.db') -> dict[int, dict[str, NPC_MD]]:
    import sqlite3
    conn = sqlite3.connect(db_path)
    npcs: dict[int, dict[str, NPC_MD]] = dict()
    with (conn):
        cursor = conn.cursor()
        sql = f'SELECT * FROM npcs'
        res = cursor.execute(sql)
        npc_rows = res.fetchall()
        for row in npc_rows:
            npc_id = row[0]
            expansion = row[1]
            name = row[2]
            tag = row[3]
            name_ua = row[4]
            tag_ua = row[5]
            type = row[6]
            boss = row[7]
            classification = row[8]
            location = row[9]
            names = row[10]
            react = row[11]
            npc = NPC_MD(npc_id, name, expansion=expansion, tag=tag, name_ua=name_ua, tag_ua=tag_ua, type=type, boss=boss,
                         classification=classification, location=location, names=names, react=react)
            npcs[npc_id] = npcs.get(npc_id, dict())
            npcs[npc_id][expansion] = npc

    return npcs

def get_zone_page(zone_id):
    import json
    url = f'https://www.wowhead.com/classic/zone={zone_id}'
    r = wowhead_get(url)
    if not r.ok:  # no such zone in the classic client
        return None

    # Every real zone page renders at least one listview, with or without NPCs. Without one we got an
    # error/interstitial page instead, and returning None would silently drop that zone's NPCs.
    if 'new Listview(' not in r.text:
        raise Exception(f'Wowhead returned an unexpected page for zone {zone_id}')

    start = r.text.find("template: 'npc'")
    if start == -1:  # No NPCs on page
        return None
    start = r.text.find('data: [', start)
    end = r.text.find('});', start)
    if start == -1 or end == -1:
        raise Exception(f'Could not read the NPC listview of zone {zone_id}')
    json_data = r.text[start + len('data: '):end]
    return (zone_id, json.loads(json_data))


def get_wowhead_zones_npc_ids(zone_ids) -> dict[int, list[int]]:
    import multiprocessing
    import pickle
    if os.path.exists(f'cache/tmp/npc_ids_to_zone_ids_cache.pkl'):
        print(f'Loading cached npc_ids_to_zone_ids')
        with open(f'cache/tmp/npc_ids_to_zone_ids_cache.pkl', 'rb') as f:
            npc_ids_to_zone_ids = pickle.load(f)
    else:
        print(f'Retrieving npc_ids_to_zone_ids data')
        npc_ids_to_zone_ids = dict()
        with multiprocessing.Pool(SCRAPE_THREADS) as p:
            npcs_by_zone = filter(lambda x: x is not None, p.map(get_zone_page, zone_ids))
        for zone_id, npcs in sorted(npcs_by_zone):
            for npc in npcs:
                if not npc['id'] in npc_ids_to_zone_ids:
                    npc_ids_to_zone_ids[npc['id']] = list()
                npc_ids_to_zone_ids[npc['id']].append(zone_id)
        os.makedirs('cache/tmp', exist_ok=True)
        with open(f'cache/tmp/npc_ids_to_zone_ids_cache.pkl', 'wb') as f:
            pickle.dump(npc_ids_to_zone_ids, f)
    return npc_ids_to_zone_ids


def merge_npc(id: int, old_npcs: dict[str, NPC_MD], new_npcs: dict[str, NPC_MD]) -> dict[str, NPC_MD]:
    if len(old_npcs) > 1 and len(new_npcs) == 1:
        # print(f'Merging more than one instance from previous expansion for NPC #{id}')
        last_old_npc_key = list(old_npcs.keys())[-1]
        result = merge_npc(id, {last_old_npc_key: old_npcs[last_old_npc_key]}, new_npcs)
        del old_npcs[last_old_npc_key]
        return {**old_npcs, **result}
    if len(old_npcs) == 1 and len(new_npcs) == 1:
        old_npc = next(iter(old_npcs.values()))
        new_npc = next(iter(new_npcs.values()))

        if old_npc.name != new_npc.name or old_npc.tag != new_npc.tag:
            return {**old_npcs, **new_npcs}
        else:
            return old_npcs
    else:
        print('-' * 100)
        print(f'Skip: NPC #{id} instance number unexpected')


def merge_expansions(old_expansion: dict[int, dict[str, NPC_MD]], new_expansion: dict[int, dict[str, NPC_MD]]) -> dict[int, dict[str, NPC_MD]]:
    result = dict()

    for id in old_expansion.keys() - new_expansion.keys():
        result[id] = old_expansion[id]

    for id in new_expansion.keys() - old_expansion.keys():
        result[id] = new_expansion[id]

    for id in old_expansion.keys() & new_expansion.keys():
        result[id] = merge_npc(id, old_expansion[id], new_expansion[id])
    return result


def fix_npc_data(all_npcs: dict[int, dict[str, NPC_MD]]):
    all_npcs[185336][CLASSIC] = all_npcs[185336][SOD]
    del all_npcs[185336][SOD]


def apply_page_data_to_metadata(expansion, metadata: dict[int, dict[str, NPC_MD]], page_data: dict[int, NPC_Data]):
    unavailable = []
    for id, npcs in metadata.items():
        npc_md = npcs[expansion]
        page_npc = page_data.get(id)
        if not page_npc:
            if npc_md.name == FORCE_LOAD_NAME:
                unavailable.append(id)
            continue
        if npc_md.name == FORCE_LOAD_NAME:
            npc_md.name = page_npc.name
            npc_md.tag = page_npc.tag
            continue
        if npc_md.name != page_npc.name:
            print(f'Warning! NPC#{id}:{expansion} name differs between search and page: '
                  f'"{npc_md.name}" <> "{page_npc.name}"')
        if npc_md.tag != page_npc.tag:
            print(f'Warning! NPC#{id}:{expansion} tag differs between search and page: '
                  f'"{npc_md.tag}" <> "{page_npc.tag}"')
    if unavailable:
        print(f'Warning! Wowhead({expansion}) has no page for force-loaded NPCs: {sorted(unavailable)}')


def retrieve_forced_npc_pages(expansion, force_ids: list[int]) -> dict[int, NPC_Data]:
    # For expansions we don't pull quotes for, only the force-loaded pages are fetched - their name/tag
    # exists nowhere else, and the full page set would be a multi-hour download.
    save_htmls_from_wowhead(expansion, set(force_ids))
    html_cache = f'cache/{expansion_data[expansion][HTML_CACHE]}'
    return {id: parse_wowhead_npc_page(expansion, id) for id in force_ids
            if os.path.exists(f'{html_cache}/{id}.html')}


def retrieve_npc_data() -> tuple[dict[int, dict[str, NPC_MD]], dict[str, dict[int, NPC_Data]]]:
    all_npcs = dict()
    npc_quotes = dict()

    for expansion, expansion_properties in expansion_data.items():
        wowhead_md = get_wowhead_npc_metadata(expansion)

        if expansion_properties[RETRIEVE_QUOTES]:
            save_htmls_from_wowhead(expansion, set(wowhead_md.keys()))
            npc_quotes[expansion] = parse_wowhead_pages(expansion, wowhead_md)
            apply_page_data_to_metadata(expansion, wowhead_md, npc_quotes[expansion])
        elif expansion_properties[FORCE_DOWNLOAD]:
            forced_pages = retrieve_forced_npc_pages(expansion, expansion_properties[FORCE_DOWNLOAD])
            apply_page_data_to_metadata(expansion, wowhead_md, forced_pages)

        print(f'Merging with {expansion}')
        all_npcs = merge_expansions(all_npcs, wowhead_md)

    fix_npc_data(all_npcs)

    return all_npcs, npc_quotes


def read_classicua_translations(entries_root_path: str) -> dict[str, dict[int, NPC_Short]]:
    return {expansion: load_npc_lua(f'{entries_root_path}/{expansion}/npc.lua')
            for expansion in expansion_data.keys()}


def apply_translations_to_data(all_npcs: dict[int, dict[str, NPC_MD]], translations: dict[str, dict[int, NPC_Short]]):
    for key in all_npcs.keys():
        for expansion in all_npcs[key].keys():
            if key in translations[expansion]:
                all_npcs[key][expansion].name_ua = translations[expansion][key].name
                all_npcs[key][expansion].tag_ua = translations[expansion][key].tag


def populate_npc_locations(all_npcs: dict[int, dict[str, NPC_MD]]):
    # Just for handier translation
    from generation.zones import zones
    wowhead_zones = zones.get_wowhead_zones()
    npc_ids_to_zone_ids = get_wowhead_zones_npc_ids(wowhead_zones.keys())

    # The search metadata already carries a per-expansion location, and the zone pages are scraped from
    # the classic client only - so the two complement each other rather than replace one another.
    for key in all_npcs.keys():
        for expansion in all_npcs[key].keys():
            npc_md = all_npcs[key][expansion]
            zone_ids = set(npc_md.location or []) | set(npc_ids_to_zone_ids.get(key, []))
            npc_md.location = sorted(zone_ids)


def update_questie_translation(all_npcs: dict[int, dict[str, NPC_MD]]):
    pass
    # questie_npcs = load_questie_npcs()
    #
    # for key in wowhead_metadata.keys() & questie_npcs.keys():
    #     wowhead_metadata[key].names = 'questie'
    #
    #
    # with open(f'lookupNpcs.lua', 'w', encoding="utf-8") as output_file:
    #     for key in wowhead_metadata.keys() & questie_npcs.keys():
    #         if not hasattr(wowhead_metadata[key], 'name_ua'):
    #             continue
    #         wowhead_metadata[key].names = 'questie'
    #         questie_name = wowhead_metadata[key].name_ua[0].upper() + wowhead_metadata[key].name_ua[1:]
    #         questie_name = '{"' + questie_name.replace('"', '\\"') + '"'
    #         questie_tag = wowhead_metadata[key].tag_ua[0].upper() + wowhead_metadata[key].tag_ua[1:] if wowhead_metadata[key].tag_ua else None
    #         questie_tag = '"' + questie_tag.replace('"', '\\"') + '"}' if questie_tag else 'nil}'
    #         output_file.write(f'[{key}] = {questie_name},{questie_tag},\n')


def __try_cast_str_to_int(value: str, default=None):
    try:
        return int(value)
    except ValueError:
        return default

def load_merged_translations() -> dict[int, dict[str, NPC_MD]]:
    import csv
    merged_translations = dict()
    with open(f'input/translations.csv', 'r', encoding="utf-8") as input_file:
        reader = csv.reader(input_file)
        for row in reader:
            npc_id = __try_cast_str_to_int(row[0])
            if not npc_id:
                print(f'Skipping: {row}')
                continue
            name_en = row[2]
            tag_en = row[3][1:-1] if row[3] != '' else None
            name_ua = row[4]
            tag_ua = row[5][1:-1] if row[5] != '' else None
            expansion = row[1]
            npc = NPC_MD(npc_id, name_en, name_ua=name_ua, tag=tag_en, tag_ua=tag_ua, expansion=expansion)
            if npc_id not in merged_translations:
                merged_translations[npc_id] = {expansion: npc}
            else:
                if expansion in merged_translations[npc_id]:
                    existing_npc = merged_translations[npc_id][expansion]
                    if existing_npc != npc:
                        print(f'Warning! NPC#{npc_id}:{expansion} duplicated and differs')
                    if existing_npc == npc:
                        print(f'Warning! NPC#{npc_id}:{expansion} duplicated')
                merged_translations[npc_id][expansion] = npc
    return merged_translations


def check_feedback_npcs(all_npcs: dict[int, dict[str, NPC_MD]]) -> set[int]:
    import csv
    feedback = dict()
    with open('input/missing_npcs.tsv', 'r', encoding='utf-8') as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        for row in reader:
            feedback[int(row[0])] = row[1]

    missed_npcs = set()
    for feedback_id, feedback_name in feedback.items():
        if feedback_id in all_npcs:
            translated = False
            for npc in all_npcs[feedback_id].values():
                if npc.name_ua:
                    translated = True
            if not translated:
                # print(f'Warning! Feedback NPC#{feedback_id} "{feedback_name}" is not translated!')
                missed_npcs.add(feedback_id)
        else:
            # print(f'Warning? Feedback NPC#{feedback_id} "{feedback_name}" does not exist in DB!')
            # missed_npcs.add(feedback_id)
            continue

    print(f'Missed IDs({len(missed_npcs)}): {sorted(missed_npcs)}')
    return missed_npcs


def compare_npc(tsv_npc: NPC_MD, lua_npc: NPC_MD):
    if tsv_npc.name != lua_npc.name:
        print(f'Warning! NPC#{tsv_npc.id}:{tsv_npc.expansion} name differs:\n{tsv_npc.name}<->{lua_npc.name}')
    if tsv_npc.tag != lua_npc.tag:
        print(f'Warning! NPC#{tsv_npc.id}:{tsv_npc.expansion} tag differs:\n{tsv_npc.tag}<->{lua_npc.tag}')
    if tsv_npc.name_ua != lua_npc.name_ua:
        print(f'Warning! NPC#{tsv_npc.id}:{tsv_npc.expansion} translation differs:\n{tsv_npc.name_ua}<->{lua_npc.name_ua}')



def check_existing_translations(all_npcs: dict[int, dict[str, NPC_MD]]):
    merged_translations = load_merged_translations()
    for key in merged_translations.keys() - all_npcs.keys():
        print(f'NPC#{key} does not exist in ClassicUA')

    for key in merged_translations.keys() & all_npcs.keys():
        for expansion in merged_translations[key].keys() - all_npcs[key].keys():
            print(f'NPC#{key}:{expansion} does not exist in ClassicUA')

        for expansion in merged_translations[key].keys() & all_npcs[key].keys():
            compare_npc(merged_translations[key][expansion], all_npcs[key][expansion])


def build_name_pretranslation_map(npcs: dict[int, dict[str, NPC_MD]]) -> dict[str, str]:
    name_translations = dict()
    for key in npcs.keys():
        for expansion, npc in sorted(npcs[key].items()):
            if npc.name_ua:
                if npc.name in name_translations and name_translations[npc.name] != npc.name_ua:
                    print(f'Warning! Name translation for {npc.name} differs: {name_translations[npc.name]} <> {npc.name_ua}')
                else:
                    name_translations[npc.name] = npc.name_ua
    return name_translations


def create_translation_sheet(npcs: dict[int, dict[str, NPC_MD]], missed_npcs: set[int] = None):
    name_pretranslation_map = build_name_pretranslation_map(npcs)
    with (open(f'translate_this.tsv', mode='w', encoding='utf-8') as f):
        f.write('ID\tName(EN)\tDescription(EN)\tName(UA)\tDescription(UA)\tраса\tстать\tNote\texpansion\n')
        count = 0
        for key in sorted(npcs.keys()):
            for expansion, npc in npcs[key].items():
                if (npc.name_ua is None and (npc.react != [None, None] or npc.location != [] or key in missed_npcs or npc.name in name_pretranslation_map.keys()) and npc.expansion in [CLASSIC, SOD, TBC]):
                    npc_name_ua = npc.name_ua if npc.name_ua else ''
                    if npc_name_ua == '' and npc.name in name_pretranslation_map.keys():
                        npc_name_ua = name_pretranslation_map[npc.name] + ' ???'
                # if npc.name_ua is None and npc.expansion in [CLASSIC, SOD]:
                # if npc.expansion in [CLASSIC, SOD] and npc.id in [14465, 14466, 229001, 232335, 202387, 202390, 222231, 202392, 202391, 14751, 222240, 205733, 230695, 7863, 8376, 212157, 11200, 213450, 229452, 222293, 7383, 232921, 2671, 2673, 2674, 228596, 11637, 7543, 7545, 223739]:
                    f.write(f'{npc.id}\t"{npc.name}"\t"{f"<{npc.tag}>" if npc.tag else ""}"\t{npc_name_ua}\t\t\t\t\t{npc.expansion}\n')
                    count += 1
        if count > 0:
            print(f"Added {count} NPCs for translation")


def save_page(expansion, id):
    url = expansion_data[expansion][WOWHEAD_URL] + f'/npc={id}'
    html_file_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    if os.path.exists(html_file_path):
        print(f'Warning! Trying to download existing HTML for #{id}')
        return
    r = wowhead_get(url)
    if not r.ok:
        # You download over 90000 pages in one hour - you'll fail
        # You do it async - you fail
        # Have a tea break (or change IP, lol)
        raise Exception(f'Wowhead({expansion}) returned {r.status_code} for NPC #{id}')
    if (f"<error>Item not found!</error>" in r.text):
        return
    with open(html_file_path, 'w', encoding="utf-8") as output_file:
        output_file.write(r.text)


def save_htmls_from_wowhead(expansion, ids: set[int]):
    from functools import partial
    import multiprocessing
    cache_dir = f'cache/{expansion_data[expansion][HTML_CACHE]}'

    os.makedirs(cache_dir, exist_ok=True)
    existing_files = os.listdir(cache_dir)
    existing_ids = set(int(file_name.split('.')[0]) for file_name in existing_files)

    if os.path.exists(cache_dir) and existing_ids == ids:
        print(f'HTML cache for all Wowhead({expansion}) NPCs ({len(ids)}) exists and seems legit. Skipping.')
        return

    save_ids = ids - existing_ids
    print(f'Saving HTMLs for {len(save_ids)} of {len(ids)} NPCs from Wowhead({expansion}).')

    redundant_ids = existing_ids - ids
    if len(redundant_ids) > 0:
        print(f"There's some redundant IDs: {redundant_ids}")

    # for id in save_ids:
    #     print(f"Saving NPC #{id}")
    #     save_page(expansion, id)
    save_func = partial(save_page, expansion)
    with multiprocessing.Pool(SCRAPE_THREADS) as p:
        p.map(save_func, save_ids)


def __parse_npc_name_and_tag(html: str, heading: str) -> tuple[str, str]:
    page_info_name = re.search(r'g_pageInfo = \{[^}]*?name: "((?:[^"\\]|\\.)*)"', html)
    if page_info_name:
        npc_name = json.loads(f'"{page_info_name.group(1)}"')  # a JS string literal: \" and \/ occur
        if heading.startswith(npc_name):
            npc_tag = heading[len(npc_name):].strip()
            if npc_tag.startswith('<') and npc_tag.endswith('>'):
                return npc_name, npc_tag[1:-1]
            return npc_name, npc_tag or None
    print(f'Warning! No usable g_pageInfo name, splitting the heading instead: "{heading}"')
    npc_name, _, npc_tag = heading.partition(' <')
    return npc_name, (npc_tag[:-1] if npc_tag.endswith('>') else npc_tag) or None


def parse_wowhead_npc_page(expansion, id) -> NPC_Data:
    # print(f"Parsing #{id}")
    html_path = f'cache/{expansion_data[expansion][HTML_CACHE]}/{id}.html'
    with open(html_path, 'r', encoding="utf-8") as file:
        html = file.read()
    soup = BeautifulSoup(html, 'html5lib')

    npc_name, npc_tag = __parse_npc_name_and_tag(html, soup.find('h1').text)
    npc_quotes_header = soup.find('h2', {'class': 'heading-size-3'}, string=re.compile('Quotes'))

    npc_quotes = list()
    if npc_quotes_header:
        npc_quotes_list = npc_quotes_header.find_next('ul').find_all('li')
        for list_element in npc_quotes_list:
            npc_quote = list_element.text[list_element.text.find(':') + 2:]
            # npc_quote = npc_quote.replace('  ', ' ')
            npc_quotes.append(npc_quote)

    return NPC_Data(id, expansion, name=npc_name, quotes=npc_quotes, tag=npc_tag)


def parse_wowhead_pages(expansion, metadata: dict[int, dict[str, NPC_MD]]) -> dict[int, NPC_Data]:
    import pickle
    import multiprocessing
    from functools import partial
    cache_path = f'cache/tmp/{expansion_data[expansion][NPC_CACHE]}.pkl'

    if os.path.exists(cache_path):
        print(f'Loading cached Wowhead({expansion}) NPCs')
        with open(cache_path, 'rb') as f:
            wowhead_npcs = pickle.load(f)
    else:
        print(f'Parsing Wowhead({expansion}) NPC pages')
        # wowhead_npcs = {id: parse_wowhead_npc_page(expansion, id) for id in metadata.keys()}
        parse_func = partial(parse_wowhead_npc_page, expansion)
        with multiprocessing.Pool(PARSE_THREADS) as p:
            wowhead_npcs = p.map(parse_func, metadata.keys())
        wowhead_npcs = {npc.id: npc for npc in wowhead_npcs}

        os.makedirs('cache/tmp', exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(wowhead_npcs, f)

    # wowhead_item_data = merge_quests_and_metadata(wowhead_items, metadata)

    # return wowhead_quest_entities
    return wowhead_npcs


def save_npc_quotes(npc_quotes: dict[str, dict[int, NPC_Data]]):
    import pickle
    os.makedirs('output', exist_ok=True)
    with open('output/all_npcs.pkl', 'wb') as f:
        pickle.dump(npc_quotes, f)
    print(f'Stored quotes for {", ".join(npc_quotes.keys())}')


def download_csv_from_google_sheet():
    output_file = 'input/translations.csv'
    sheet_id = '1xwoaO6U-jXQChHecEzzqG-leESTmRKm2WXHev4GOFho'
    url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=NPCs'
    print('Downloading translations from Google Sheet... ', end='')
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(response.text.replace('\r\n', '\n'))
        print('Done!')
    else:
        print(f'Error downloading sheet: {response.status_code} - {response.text}')



if __name__ == '__main__':
    download_csv_from_google_sheet()

    all_npcs_md, npc_quotes = retrieve_npc_data()

    populate_npc_locations(all_npcs_md)

    classicua_translations = read_classicua_translations('input/entries')
    apply_translations_to_data(all_npcs_md, classicua_translations)

    save_npcs_to_db(all_npcs_md)  # Generate cache/npcs.db
    save_npc_quotes(npc_quotes)  # Generate output/all_npcs.pkl

    check_existing_translations(all_npcs_md)  # Check if original data changes since previous translation and difference between ClassicUA and translation sheet
    # update_questie_translation(all_npcs)  # Update translations for Questie

    missed_npcs = check_feedback_npcs(all_npcs_md)

    # create_translation_sheet(all_npcs_md)
    create_translation_sheet(all_npcs_md, missed_npcs)

