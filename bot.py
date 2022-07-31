import json
import random
import time
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


def convert(a):
    it = iter(a)
    res_dct = dict(zip(it, it))
    return res_dct


class join_game(miru.View):
    players = []

    @miru.button(label="Join", style=hikari.ButtonStyle.SUCCESS)
    async def start_button(self, button: miru.Button, ctx: miru.Context) -> None:

        join_game.players.append(str(ctx.user.id))
        resp = "> Players: "
        for i in range(len(join_game.players)):
            if resp.find(str(ctx.user.id)) == -1:
                resp += "<@" + join_game.players[i] + "> "
        await ctx.edit_response(resp)
        bot.d = join_game.players

        # player.append(ctx.user.id)

    @miru.button(label="Start", style=hikari.ButtonStyle.DANGER)
    async def stop_button(self, button: miru.Button, ctx: miru.Context):
        join_game.players = []
        self.stop()  # Stop listening for interactions

    async def on_timeout(self) -> None:
        bot.d = "Timeout"


class answers(miru.View):
    @miru.button(emoji=hikari.Emoji.parse("🇦"), style=hikari.ButtonStyle.PRIMARY)
    async def a_button(self, button: miru.Button, ctx: miru.Context) -> None:
        bot.d = ["A", ctx.user.id]
        self.stop()

    @miru.button(emoji=hikari.Emoji.parse("🇧"), style=hikari.ButtonStyle.PRIMARY)
    async def b_button(self, button: miru.Button, ctx: miru.Context) -> None:
        bot.d = ["B", ctx.user.id]
        self.stop()

    @miru.button(emoji=hikari.Emoji.parse("🇨"), style=hikari.ButtonStyle.PRIMARY)
    async def c_button(self, button: miru.Button, ctx: miru.Context) -> None:

        bot.d = ["C", ctx.user.id]
        self.stop()

    @miru.button(emoji=hikari.Emoji.parse("🇩"), style=hikari.ButtonStyle.PRIMARY)
    async def d_button(self, button: miru.Button, ctx: miru.Context) -> None:
        bot.d = ["D", ctx.user.id]
        self.stop()

    @miru.button(emoji=hikari.Emoji.parse("🛑"), style=hikari.ButtonStyle.DANGER)
    async def stop_button(self, button: miru.Button, ctx: miru.Context) -> None:
        bot.d = ["Stop", ctx.user.id]
        self.stop()

    async def on_timeout(self) -> None:
        bot.d = "Timeout"


@bot.command
@lightbulb.option('url', 'Quizlet set url', type=str)
@lightbulb.command('start-game', 'Starts quizlet game')
@lightbulb.implements(lightbulb.SlashCommand)
async def pic(ctx: lightbulb.SlashContext):
    await (await ctx.respond("Starting Game...")).message()
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
    if str(bot.d) == "Timeout":
        await ctx.delete_last_response()
        return
    playerList = bot.d
    del bot.d
    for player in range(len(playerList)):
        playerList.insert(playerList.index(playerList[player]) * 2 + 1, 0)

    playerMap = convert(playerList)
    del playerList
    cnt = 0
    stop = True
    while stop:
        view = answers(timeout=10)
        data = get_quiz_data(orig_quizlet_set, remain_quizlet_set)
        cnt += 1
        embed = hikari.Embed(title="Round " + str(cnt),
                             description="Match the terms (10 seconds to answer)\n\nTerm: **" + data[
                                 1] + "**\n\nAnswers:\n:regional_indicator_a:: " + data[0][
                                             0] + "\n:regional_indicator_b:: " + data[0][
                                             1] + "\n:regional_indicator_c:: " +
                                         data[0][2] + "\n:regional_indicator_d:: " + data[0][3], color=0x4257b2)
        embed.set_footer(text="Set ID: " + set_id)
        prompt = await ctx.edit_last_response("", embed=embed, components=view.build())
        view.start(prompt)
        await view.wait()  # Wait until the view times out or gets stopped
        if str(bot.d) == "Timeout":
            continue
        if str(bot.d[0]) == "Stop":
            stop = False
            continue
        letter = correct_letter(data)
        if str(bot.d[0]) == letter:
            playerMap[str(bot.d[1])] += 10
            resp = "correct :white_check_mark:\n> Good job " + "<@" + str(bot.d[1]) + ">\n> You have " + str(
                playerMap[str(bot.d[1])]) + " points!"
        else:
            playerMap[str(bot.d[1])] -= 10
            resp = "incorrect :x:\n> <@" + str(bot.d[1]) + "> answered: " + str(bot.d[0]) + "\n> You have " + str(
                playerMap[str(bot.d[1])]) + " points."

        await ctx.respond("The last answer was **" + data[2] + "** or answer **" + letter + "**\n> " + "<@" + str(
            bot.d[1]) + "> is " + resp)
        del remain_quizlet_set[data[2]]
        time.sleep(6)
        await ctx.delete_last_response()

    myList = sorted(playerMap.items(), key=lambda x: x[1], reverse=True)
    rank = ""
    for i in range(len(myList)):
        rank += str(i + 1) + ". <@" + str(myList[i][0]) + "> " + str(playerMap[str(myList[i][0])]) + " Points\n"

    embed = hikari.Embed(title="🏆 Rankings 🏆", description=rank, color=0x4257b2)
    embed.set_footer(text="Thanks for playing!")
    await ctx.respond("", embed=embed)


miru.load(bot)
bot.run()
