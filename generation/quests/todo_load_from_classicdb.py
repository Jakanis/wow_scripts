# # ClassicDB page parsing need to be improved to have less errors.
# # Currently just merging new changes from Wowhead without deletion of existing data from ClassicUA DB (or doing that manually if needed)
#
#
# def __get_classicdb_objective_text(soup: BeautifulSoup):
#     out = None
#
#     tag = soup.find('h1')
#     if tag:
#         out = __cleanup_text(__get_forward_text(tag))
#     if 'Additional requirements to obtain this quest' in out:
#         line = tag.parent.find('div', class_='line')
#         if line:
#             out = __cleanup_text(__get_forward_text(line))
#
#     return out if out and out.strip() != '' else None
#
#
# def __get_classicdb_description_text(soup):
#     out = None
#
#     tag = soup.find('h3', string='Description')
#     if tag:
#         out = __cleanup_text(__get_forward_text(tag))
#
#     return out
#
#
# def __get_classicdb_progress_text(soup):
#     out = None
#
#     tag = soup.find('div', id='progress')
#     if tag:
#         out = __cleanup_text(tag.get_text())
#
#     return out
#
#
# def __get_classicdb_completion_text(soup):
#     out = None
#
#     tag = soup.find('div', id='completion')
#     if tag:
#         out = __cleanup_text(tag.get_text())
#
#     return out
#
# def __parse_classicdb_quest_page(id) -> Quest:
#     if not os.path.exists(f'cache/classicdb_quests_html/{id}.html'):
#         return Quest(id, None)
#     with open(f'cache/classicdb_quests_html/{id}.html', 'r', encoding="utf-8") as file:
#         html = file.read()
#     soup = BeautifulSoup(html, 'html5lib').find('div', id='main-contents')
#
#     for br in soup.find_all('br'):
#         br.replace_with('$LINEBREAK$')
#
#     quest_name = soup.find('h1').text
#     objective = __get_classicdb_objective_text(soup)
#     description = __get_classicdb_description_text(soup)
#     progress = __get_classicdb_progress_text(soup)
#     completion = __get_classicdb_completion_text(soup)
#
#     return Quest(id, quest_name, objective, description, progress, completion)
#
# def parse_classicdb_pages(wowhead_metadata: dict[int, QuestMD]) -> dict[int, Quest]:
#     import pickle
#     if os.path.exists("cache/tmp/classicdb_quest_cache.pkl"):
#         print('Loading saved ClassicDB quests')
#         with open('cache/tmp/classicdb_quest_cache.pkl', 'rb') as f:
#             classicdb_quests = pickle.load(f)
#     else:
#         print('Parsing ClassicDB quest pages')
#         # quests = {id: __parse_classicdb_quest_page(id) for id in wowhead_metadata.keys()}
#         with multiprocessing.Pool(THREADS) as p:
#             quests = p.map(__parse_classicdb_quest_page, wowhead_metadata.keys())
#         classicdb_quests = {quest.id: quest for quest in quests}
#         os.makedirs('cache/tmp', exist_ok=True)
#         with open('cache/tmp/classicdb_quest_cache.pkl', 'wb') as f:
#             pickle.dump(classicdb_quests, f)
#     return classicdb_quests
#
#
# def fix_quests(quests):
#     quests[33].description = quests[33].description.replace('\ntough wolf meat', '\nTough wolf meat')
#     quests[57].progress = 'Return to me once you have killed 15 Skeletal Fiends and 15 Skeletal Horrors, <name>.'
#     quests[97].progress = 'Yes, <name>?'
#     quests[128].progress = 'Return once you have slain 15 Blackrock Champions.'
#     quests[155].progress = 'What business do you have with me? I am a very busy man...'
#     quests[156].description = quests[156].description.replace('\nrot blossoms grow in strange places.', '\nRot blossoms grow in strange places.')
#     quests[172].completion = quests[172].completion.replace('be like a big brother to me', 'be like a big <brother/sister> to me')
#     quests[201].progress = 'Well? Did you have any luck in locating the camp?'
#     quests[245].progress = "You'd best be careful when dealing with the spiders, I've lost a few of my men to them, and trust me, it isn't a pleasant sight to see a man hanging upside down in their webs after the venom has started to soften them up.\n\nI wouldn't want to see one of the bugs having you for lunch."
#     quests[434].progress = "Yes, <name>? Are things going well with Tyrion? He apprised me of the situation and I've helped him trick Marzon into going to the castle.\n\nMarzon has been a thorn in the side of many people in Stormwind; many of which are close friends of mine. No one messes with my friends... not if they know what's healthy for them.\n\nIt's just a shame I'm indirectly doing a favor for Shaw and SI:7 in the meantime. Oh well, not every plan is perfect."
#     quests[455].progress = "You're coming from Loch Modan? How is the orc situation at Algaz Gate?"
#     quests[504].progress = "You have more Warmongers to slay, <name>. You should be up on the mountains on your task, not down here with your weapon stowed."
#     quests[505].progress = "You have slain those Syndicate thugs, I trust?"
#     quests[516].progress = "Have you located their base yet, <name>? Time is of the essence!"
#     quests[564].progress = "Mountain Lions killin' off our horses left and right and here you are wantin' to jibber-jabber about the weather and what not.\n\nOught to go and find myself a real hero. More killin' and less talkin'."
#     quests[578].progress = "The trolls truly possessed some amazing magical objects, <name>. And now, perhaps, I have the opportunity to add one to my extensive collection. Did you have any luck finding the source of the rumor?"
#     # metadata[593].side = 2 # horde
#     quests[614].progress = "Ahoy, <name>! Did you find Gorlash? That chest was my favorite, and it has a hidden compartment that held my greatest treasures!"
#     quests[614].completion = "You found it! Oh happy day, this is! Thank you, <name>. Getting back my chest cools some of the fire in me.\n\nBut my revenge isn't complete..."
#     quests[615].completion = "Hello hello, <name>. Captain told me you're going after Negolash, eh?"
#     quests[618].progress = "Did you get my cutlass, <name>?"
#     quests[618].completion = "You got my cutlass from Negolash! I can't believe my fortune, <name>! Meeting you has turned my luck to the better, make no mistake there!\n\nThank you! And if I ever get a new ship and you're looking to sail the seas, you would be my honored guest."
#     quests[679].progress = "I see your courage finally wanes. It seems my instincts were correct about you: your strength is nothing compared to your bravado.\n\nReturn to me when the beast's head has been severed, or return never again."
#     # metadata[708].side = 1 # alliance
#     quests[731].progress = "Is the prospector alive?"
#     quests[739].progress = "Do you have news of Agmond's fate? Did you find him?"
#     quests[745].progress = "If the Palemanes had respected the land and its inhabitants more, this conflict would have never occurred."
#     quests[812].completion += ' <sigh>'
#     quests[842].completion = "Alright, <name>. You want to earn your keep with the Horde? Well there's plenty to do here, so listen close and do what you're told.\n\n<I see that look in your eyes, do not think I will tolerate any insolence. Thrall himself has declared the Hordes females to be on equal footing with you men. Disrespect me in the slightest, and you will know true pain./I'm happy to have met you. Thrall will be glad to know that more females like you and I are taking the initiative to push forward in the Barrens.>"
#     quests[863].progress = "Can I help you?"
#     quests[895].description = quests[895].description.replace('and is WANTED on', 'and is wanted on')
#     quests[908].progress = "Have you been successful in locating the fathom core? Without it we'll have no idea what the Twilight's Hammer is exactly up to down there."
#     quests[908].completion = "This is exactly what I need! A fathom core is an incredible well of information that we will be able to draw much good from. Whatever the Twilight's Hammer is up to in there - and believe me when I say it is no good - my comrades and I will now uncover.\n\nYou've done well here today; the Earthen Ring looks upon you warmly for assisting us. You've also helped the Horde as a whole, and for that you should be proud."
#     # metadata[908].side = 2 # horde
#     quests[909].progress = "Ah, hello again <name>. I was just reading the waves the sea, much like I always do. What brings you to the outpost?"
#     quests[909].completion = "This... this is quite the find, <name>.\n\nYou acquired this from Baron Aquanis in Blackfathom, you say? Baron Aquanis has long been thought of as a corrupted elemental power; this globe will prove what exactly had corrupted him. While it would be no surprise if it turned out to be the Twilight's Hammer, our studies will also show how they did it as well.\n\nYou did well in bringing this to me. Please - take this, along with the Earthen Ring's warmest regards."
#     quests[910].progress = "Are we there yet?"
#     quests[934].progress = "Along with the druids, the Oracle Tree and the Arch Druid have been carefully monitoring the growth of Teldrassil. But though we have a new home, our immortal lives have not been restored."
#     quests[934].completion = "To be in the presence of the Oracle Tree... it is almost to feel wisdom take form. Let me continue the telling...\n\nWith Teldrassil grown, the Arch Druid approached the dragons for their blessings, as the dragons had placed upon Nordrassil in ancient times. But Nozdormu, Lord of Time, refused to give his blessing, chiding the druid for his arrogance. In agreement with Nozdormu, Alexstrasza also refused Staghelm, and without her blessing, Teldrassil's growth has been flawed and unpredictable..."
#     quests[985].progress = "Do not stay your hand from what must be done, child. I know how repulsive the idea of killing the creatures of the forest must be, but in this case it is necessary. No cure has been discovered for the corruption let loose upon the forest, and we must do what we can to halt its progress until one is found."
#     quests[995].progress = "Yes, <name>?"
#     quests[1025].progress = "The furbolg were not always our enemy, <name>. But times change, and it is no longer a time of peace here in these dark woods."
#     quests[1053].progress = "The corruption in the Monastery will not end until the highest ranking officials have been removed.\n\nIn the name of the Light, slay High Inquisitor Whitemane, Scarlet Commander Mograine, Herod, the Scarlet Champion and Houndmaster Loksey. Once they have fallen, perhaps the true cause can be rekindled. Until then, anyone who crosses the path of the Crusade lies in peril.\n\nVenture forth from Southshore and make it so!"
#     quests[1127].progress = "Do you have those Zanzil mixtures yet, <name>?"
#     quests[1127].completion = "Ah, very good! Here is your pay.\n\nAnd here is a little something extra... for your discretion."
#     quests[1146].progress = "With the amount of travelers heading out to the Flats for those races, I'm sure we can convince enough adventure seekers to help push back those insects. My party and I won't be able to leave until we do."
#     quests[1168].progress = "Mok'Morokk tell all ogres to stay and keep this place safe. Me think ogres need to kill black dragon army and get old home back.\n\nYou help ogres get home back. Help ogres get revenge."
#     quests[1173].progress = "I thought you were going to attempt to drive Mok'Morokk out of the village. Instead you have come to me to chat?"
#     quests[1222].progress = "Have you seen Mr. Ignatz? I sent him into the swamp some time ago and he hasn't returned!"
#     quests[1273].progress = "Did you find Reethe?"
#     quests[1288].completion = "Well, judging from Captain Vimes's report, you've been a huge help to his investigation, and for that I thank you.\n\nI can put my mind more at ease knowing that the matter is in such capable hands. If you would, I would request that you return to Captain Vimes and help him in getting to the bottom of this mystery."
#     quests[1361].progress = "I note that your task is unfinished, <name>. Shall I inform Sharlindra of your ineptitude?"
#     quests[1468].completion = quests[1468].completion.replace('be like a big brother to me', 'be like a big <brother/sister> to me').replace(', yes sir.', ', yes <sir/lady>.')
#     quests[1657].progress = 'Have you delivered our "gift" to the people of Southshore?\n\n<Darkcaller Yanka laughs wickedly.>'
#     quests[1788].progress = "You've done well this day, <name>. You should take some pride in what you've accomplished.\n\nEven more so, you should be proud of your abilities. Not everyone can use the power of the Symbol of Life. Calling upon the Light to bring back the dead means you're prepared for one of the <class>'s greatest honors: the power of resurrection.\n\nYou shall have the power to bring back fallen companions much like you did for Henze.\n\nBe well, <name>. The Light shines upon you and you should welcome it wholly."
#     quests[1824].progress = "Do you have the antennae? If so then give them to me quickly, for twitching antennae do not twitch forever..."
#     quests[1824].completion = "Nicely done, <name>! In passing the trial at the Field of Giants, you take one more step down the <class>'s path."
#     quests[1955].progress = "You'll have to kill that demon to remove its taint from the orb, <name>."
#     # quests[2881].objective = None
#     # quests[3570].objective = None
#     # quests[4083].objective = None
#     # quests[4103].objective = None
#     # quests[4108].objective = None
#     # quests[4144].objective = None
#     # quests[4803].objective = None
#     # quests[4804].objective = None
#     # quests[4805].objective = None
#     # quests[4807].objective = None
#     # quests[5042].progress = quests[5042].objective
#     # quests[5042].objective = None
#     # quests[5044].objective = None
#     # quests[5044].progress += ' <snort>'
#     # quests[5265].description = quests[5265].description.replace('the Argent Hold is now open', 'The Argent Hold is now open')
#     # quests[5505].objective = None
#     # quests[5511].objective = None
#     # quests[6846].progress = quests[6846].objective
#     # quests[6846].objective = None
#     # quests[6901].progress = quests[6901].objective
#     # quests[6901].objective = None
#     # quests[7002].objective = None
#     # quests[7026].objective = None
#     # quests[7341].progress = quests[7341].objective
#     # quests[7341].objective = None
#     # quests[7421].progress = quests[7421].objective
#     # quests[7422].progress = quests[7422].objective
#     # quests[7423].progress = quests[7423].objective
#     # quests[7424].progress = quests[7424].objective
#     # quests[7425].progress = quests[7425].objective
#     # quests[7426].progress = quests[7426].objective
#     # quests[7427].progress = quests[7427].objective
#     # quests[7428].progress = quests[7428].objective
#     # quests[7653].objective = None
#     # quests[7654].objective = None
#     # quests[7657].objective = None
#     # quests[7659].objective = None
#     # quests[7737].objective = None
#     # quests[7796].objective = None
#     # quests[7801].objective = None
#     # quests[7802].objective = None
#     # quests[7804].objective = None
#     # quests[7806].objective = None
#     # quests[7807].objective = None
#     # quests[7812].objective = None
#     # quests[7813].objective = None
#     # quests[7817].objective = None
#     # quests[7825].objective = None
#     # quests[7832].objective = None
#     # quests[7837].objective = None
#     # quests[7838].objective = None
#     # quests[7886].progress = quests[7886].objective
#     # quests[7886].objective = None
#     # quests[7887].progress = quests[7887].objective
#     # quests[7887].objective = None
#     # quests[7888].progress = quests[7888].objective
#     # quests[7888].objective = None
#     # quests[7921].progress = quests[7921].objective
#     # quests[7921].objective = None
#     # quests[7922].progress = quests[7922].objective
#     # quests[7922].objective = None
#     # quests[7923].progress = quests[7923].objective
#     # quests[7923].objective = None
#     # quests[7924].progress = quests[7924].objective
#     # quests[7924].objective = None
#     # quests[7925].progress = quests[7925].objective
#     # quests[7925].objective = None
#     # quests[7936].completion = quests[7936].completion.replace('A prize fit for a king!', 'A prize fit for a <king/queen>!')
#     # quests[8044].progress = quests[8044].objective
#     # quests[8044].objective = None
#     # quests[8046].completion += "\n\n<Jin'rokh shudders.>"
#
# def merge_quests(wowhead_quests: dict[int, Quest], classicdb_quests: dict[int, Quest], metadata: dict[int, QuestMD]):
#     import Levenshtein
#     from utils import not_used_vanilla_quests
#     quests = dict()
#
#     for id in metadata.keys():
#         wowhead_quest = wowhead_quests[id]
#         classicdb_quest = classicdb_quests[id]
#
#         # Skip not used quests
#         if (id in not_used_vanilla_quests or
#             '<UNUSED>' in wowhead_quest.name.upper() or
#             '<NYI>' in wowhead_quest.name.upper() or
#             '<TXT>' in wowhead_quest.name.upper() or
#             '<CHANGE TO GOSSIP>' in wowhead_quest.name.upper() or
#             '<TEST>' in wowhead_quest.name.upper() or
#             '[DEPRECATED]' in wowhead_quest.name.upper() or
#             'iCoke' in wowhead_quest.name or
#             'REUSE' in wowhead_quest.name.upper()):
#             continue
#
#         # if (wowhead_quest.name != classicdb_quest.name):
#         #     print(f'Name diff {id}: {wowhead_quest.name} <> {classicdb_quest.name}')
#
#         # if (wowhead_quest != classicdb_quest):
#         #     print(f'DIFF {id}:')
#         #     print(wowhead_quest.diff(classicdb_quest))
#
#         objective = wowhead_quest.objective if wowhead_quest.objective else classicdb_quest.objective
#         description = wowhead_quest.description if wowhead_quest.description else classicdb_quest.description
#         progress = wowhead_quest.progress if wowhead_quest.progress else classicdb_quest.progress
#         completion = wowhead_quest.completion if wowhead_quest.completion else classicdb_quest.completion
#
#         # For quests like #16, when we parse first text after quest name as objective
#         if objective and progress and Levenshtein.ratio(objective, progress) > 0.99:
#             objective = None
#         if description and progress and Levenshtein.ratio(description, progress) > 0.99:
#             description = None
#         if objective == 'null':
#             objective = None
#         # if not objective or not description:
#         #     objective = None
#         #     description = None
#
#         quests[id] = Quest(id, wowhead_quest.name, objective, description, progress, completion)
#
#     return quests
#

# CLASSICDB_URL = 'https://classicdb.ch'
# def __save_classicdb_html_page(id):
#     url = CLASSICDB_URL + f'/?quest={id}'
#     r = requests.get(url)
#     if ("This quest doesn't exist in our database" in r.text):
#         return
#     with open(f'./cache/classicdb_quests_html/{id}.html', 'w', encoding="utf-8") as output_file:
#         output_file.write(r.text)
#
# def save_htmls_from_classicdb(ids: list[int]):
#     print(f'Saving HTMLs for {len(ids)} quests from ClassicDB.')
#
#     os.makedirs('cache/classicdb_quests_html', exist_ok=True)
#     with multiprocessing.Pool(THREADS) as p:
#         p.map(__save_classicdb_html_page, ids)