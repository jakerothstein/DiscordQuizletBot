import json
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import hikari
import miru
import lightbulb
import re

CHROMEDRIVER_PATH = "C:\Program Files (x86)\chromedriver.exe"
options = Options()
options.headless = True
driver = webdriver.Chrome(CHROMEDRIVER_PATH,
                          chrome_options=options)  # Quizlet uses CloudFlare effectively blocking API requests so to get around this you can use selenium

bot = lightbulb.BotApp(
    token=''  # DISCORD BOT TOKEN
)


def get_quizlet_data(set_id):
    url = "https://quizlet.com/webapi/3.4/studiable-item-documents?filters%5BstudiableContainerId%5D=" + str(
        set_id) + "&filters%5BstudiableContainerType%5D=1&perPage=1000&page=1"
    driver.get(url)

    data = driver.find_element_by_css_selector("pre").get_attribute('innerHTML')

    parsed = json.loads(data)

    num_cards = parsed['responses'][0]['paging']['total']
    parsed_data = parsed['responses'][0]['models']['studiableItem']  # [0]['cardSides']

    return [parsed_data, num_cards]


def get_quizlet_attributes(set_id):
    output = get_quizlet_data(set_id)
    quizlet_set = {}
    for i in range(output[1]):
        quizlet_set[output[0][i]['cardSides'][0]['media'][0]['plainText']] = output[0][i]['cardSides'][1]['media'][0][
            'plainText']
    return quizlet_set


def get_quiz_data(orig_quizlet_set, remain_quizlet_set):
    ans_options = []
    answer = random.choice(list(remain_quizlet_set.keys()))
    prompt = remain_quizlet_set[answer]
    ans_options.append(answer)
    while len(ans_options) < 4:
        option = random.choice(list(orig_quizlet_set.keys()))
        if option not in ans_options:
            ans_options.append(option)
    random.shuffle(ans_options)
    return [ans_options, prompt, answer]


def correct_letter(data):
    for i in range(len(data[0])):
        if data[0][i] == data[2]:
            if i == 0:
                return "A"
            elif i == 1:
                return "B"
            elif i == 2:
                return "C"
            else:
                return "D"
class join_game(miru.View):
    @miru.button(label="Join", style=hikari.ButtonStyle.SUCCESS)
    async def start_button(self, button: miru.Button, ctx: miru.Context) -> None:
        await ctx.respond("<@" + str(ctx.user.id) + ">" + " joined")
        # player.append(ctx.user.id)

    @miru.button(label="Start", style=hikari.ButtonStyle.DANGER)
    async def stop_button(self, button: miru.Button, ctx: miru.Context):
        self.stop()  # Stop listening for interactions


class answers(miru.View):
    @miru.button(emoji=hikari.Emoji.parse("🇦"), style=hikari.ButtonStyle.PRIMARY)
    async def a_button(self, button: miru.Button, ctx: miru.Context) -> None:
        bot.d = "A"
        self.stop()

    @miru.button(emoji=hikari.Emoji.parse("🇧"), style=hikari.ButtonStyle.PRIMARY)
    async def b_button(self, button: miru.Button, ctx: miru.Context) -> None:
        bot.d = "B"
        self.stop()

    @miru.button(emoji=hikari.Emoji.parse("🇨"), style=hikari.ButtonStyle.PRIMARY)
    async def c_button(self, button: miru.Button, ctx: miru.Context) -> None:
        bot.d = "C"
        self.stop()

    @miru.button(emoji=hikari.Emoji.parse("🇩"), style=hikari.ButtonStyle.PRIMARY)
    async def d_button(self, button: miru.Button, ctx: miru.Context) -> None:
        bot.d = "D"
        self.stop()


@bot.command
@lightbulb.option('url', 'Quizlet set url', type=str)
@lightbulb.command('start-game', 'Starts quizlet game')
@lightbulb.implements(lightbulb.SlashCommand)
async def pic(ctx: lightbulb.SlashContext):
    msg = await (await ctx.respond("Starting Game...")).message()
    players = []
    view = join_game(timeout=60)

    url = ctx.options.url
    set_id = re.sub("[^0-9]", "", url)
    orig_quizlet_set = get_quizlet_attributes(set_id)
    remain_quizlet_set = orig_quizlet_set

    embed = hikari.Embed(title="Quizlet Bot", description="**Game Started!**\n*Press Join to enter the game*",
                         color=0x4257b2, url=url)
    embed.set_thumbnail("https://www.aisd.net/wp-content/files/quizlet.png")
    embed.set_footer(text="Set ID: " + set_id)

    message = await ctx.edit_last_response("", embed=embed, components=view.build())
    view.start(message)
    await view.wait()  # Wait until the view times out or gets stopped

    data = get_quiz_data(orig_quizlet_set, remain_quizlet_set)
    view = answers(timeout=10)

    cnt = 0
    cnt += 1
    embed = hikari.Embed(title="Round " + str(cnt),
                         description="Match the terms (10 seconds to answer)\n\nTerm: **" + data[
                             1] + "**\n\nAnswers:\n:regional_indicator_a:: " + data[0][
                                         0] + "\n:regional_indicator_b:: " + data[0][1] + "\n:regional_indicator_c:: " +
                                     data[0][2] + "\n:regional_indicator_d:: " + data[0][3], color=0x4257b2)
    embed.set_footer(text="Set ID: " + set_id)
    prompt = await ctx.edit_last_response(embed=embed, components=view.build())
    view.start(message)
    await view.wait()  # Wait until the view times out or gets stopped
    letter = correct_letter(data)
    await ctx.respond("The last answer was **" + data[2] + "** or answer **" + letter + "**\nYou answered " + str(bot.d))


miru.load(bot)
bot.run()
