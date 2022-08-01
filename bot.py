import json
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import hikari
import miru
import lightbulb
import urllib.parse

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
    try:
        num_cards = parsed['responses'][0]['paging']['total']
        parsed_data = parsed['responses'][0]['models']['studiableItem']  # [0]['cardSides']
        return [parsed_data, num_cards]
    except:
        return "Error"


def get_quizlet_attributes(set_id):
    output = get_quizlet_data(set_id)
    if output == "Error":
        return "Error"
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


def get_start_players_str(players_lst, user_id):
    resp = "> Players: "
    for i in range(len(players_lst)):
        if resp.find(str(user_id)) == -1:
            resp += "<@" + players_lst[i] + "> "
    return resp


class join_game(miru.View):
    players = []

    @miru.button(label="Join", style=hikari.ButtonStyle.SUCCESS)
    async def start_button(self, button: miru.Button, ctx: miru.Context) -> None:
        global int_user_used
        global init_user

        if not int_user_used:
            int_user_used = True
            join_game.players.append(init_user)

        if str(ctx.user.id) not in join_game.players:
            join_game.players.append(str(ctx.user.id))
            resp = get_start_players_str(join_game.players, ctx.user.id)
            await ctx.edit_response(resp)
            bot.d = join_game.players
        else:
            await ctx.respond("You have already joined the party!",
                              flags=hikari.MessageFlag.EPHEMERAL)

        # player.append(ctx.user.id)

    @miru.button(label="Start", style=hikari.ButtonStyle.PRIMARY)
    async def stop_button(self, button: miru.Button, ctx: miru.Context):
        global int_user_used
        global init_user

        if not int_user_used:
            int_user_used = True
            join_game.players.append(init_user)

        if str(ctx.user.id) == str(init_user):
            bot.d = join_game.players
            join_game.players = []
            self.stop()  # Stop listening for interactions
        else:
            await ctx.respond("You must be the leader of the party in order to start the game!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(label="Leave", style=hikari.ButtonStyle.DANGER)
    async def leave_button(self, button: miru.Button, ctx: miru.Context):
        global int_user_used
        global init_user

        if not int_user_used:
            int_user_used = True
            join_game.players.append(init_user)

        if str(ctx.user.id) in join_game.players:
            join_game.players.remove(str(ctx.user.id))
            resp = get_start_players_str(join_game.players, ctx.user.id)
            await ctx.edit_response(resp)
            bot.d = join_game.players
            if init_user not in join_game.players:
                await ctx.edit_response("> *This game was ended because the leader left the party*", embeds="",
                                        components="")
                bot.d = "Timeout1"
                self.stop()

        else:
            await ctx.respond("You can't leave if you are not the party!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(label="Cancel", style=hikari.ButtonStyle.SECONDARY)
    async def cancel_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) == str(init_user):
            bot.d = "Timeout"
            global gameStarted
            gameStarted = False
            global int_user_used
            int_user_used = False
            self.stop()
        else:
            await ctx.respond("You must be the leader of the party to cancel the game",
                              flags=hikari.MessageFlag.EPHEMERAL)

    async def on_timeout(self) -> None:
        bot.d = "Timeout"


class answers(miru.View):
    @miru.button(emoji=hikari.Emoji.parse("🇦"), style=hikari.ButtonStyle.PRIMARY)
    async def a_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) in playerMap:
            bot.d = ["A", ctx.user.id]
            self.stop()
        else:
            await ctx.respond("You are not part of this game. Join a game next round!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji=hikari.Emoji.parse("🇧"), style=hikari.ButtonStyle.PRIMARY)
    async def b_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) in playerMap:
            bot.d = ["B", ctx.user.id]
            self.stop()
        else:
            await ctx.respond("You are not part of this game. Join a game next round!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji=hikari.Emoji.parse("🇨"), style=hikari.ButtonStyle.PRIMARY)
    async def c_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) in playerMap:
            bot.d = ["C", ctx.user.id]
            self.stop()
        else:
            await ctx.respond("You are not part of this game. Join a game next round!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji=hikari.Emoji.parse("🇩"), style=hikari.ButtonStyle.PRIMARY)
    async def d_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) in playerMap:
            bot.d = ["D", ctx.user.id]
            self.stop()
        else:
            await ctx.respond("You are not part of this game. Join a game next round!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji=hikari.Emoji.parse("🛑"), style=hikari.ButtonStyle.DANGER)
    async def stop_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) in playerMap:
            bot.d = ["Stop", ctx.user.id]
            global gameStarted
            gameStarted = False
            global int_user_used
            int_user_used = False
            self.stop()
        else:
            await ctx.respond("You are not part of this game. Join a game next round!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    async def on_timeout(self) -> None:
        bot.d = "Timeout"


playerMap = {}

gameStarted = False

init_user = ""

int_user_used = False


@bot.command
@lightbulb.option('url', 'Quizlet set url', type=str)
@lightbulb.command('start-game', 'Starts quizlet game')
@lightbulb.implements(lightbulb.SlashCommand)
async def quizlet_game(ctx: lightbulb.SlashContext):
    global int_user_used
    int_user_used = False
    global init_user
    init_user = str(ctx.author.id)
    global gameStarted
    if gameStarted:
        await ctx.respond("There is already a game in progress!", flags=hikari.MessageFlag.EPHEMERAL)
        time.sleep(1)
        return
    await (await ctx.respond("Starting Game...")).message()
    gameStarted = True
    view = join_game(timeout=60)
    url = str(ctx.options.url)

    # set_id = re.sub("[^0-9]", "", url)
    parsed = urllib.parse.urlsplit(url)
    set_id = parsed.path.split("/")[1]

    orig_quizlet_set = get_quizlet_attributes(set_id)

    if orig_quizlet_set == "Error":
        gameStarted = False
        await ctx.edit_last_response("> **Invalid set url**\nPlease check your url")
        return
    remain_quizlet_set = orig_quizlet_set

    embed = hikari.Embed(title="Quizlet Bot", description="**Game Started!**\n*Press Join to enter the party*",
                         color=0x4257b2, url="https://github.com/jakerothstein/DiscordQuizletBot")
    embed.set_thumbnail("https://www.aisd.net/wp-content/files/quizlet.png")
    embed.set_footer(text="Set ID: " + set_id + " - https://quizlet.com/" + set_id)

    message_str = "> Players: <@" + str(ctx.author.id) + ">"
    message = await ctx.edit_last_response(message_str, embed=embed, components=view.build())
    view.start(message)
    await view.wait()  # Wait until the view times out or gets stopped
    if str(bot.d) == "Timeout":
        await ctx.delete_last_response()
        gameStarted = False
        return
    elif str(bot.d) == "Timeout1":
        gameStarted = False
        return
    playerList = bot.d
    del bot.d
    for player in range(len(playerList)):
        playerList.insert(playerList.index(playerList[player]) * 2 + 1, 0)
    global playerMap
    playerMap = convert(playerList)
    del playerList
    cnt = 0
    stop = True
    while stop:
        view = answers(timeout=20)
        data = get_quiz_data(orig_quizlet_set, remain_quizlet_set)
        cnt += 1
        embed = hikari.Embed(title="Round " + str(cnt),
                             description="Match the terms (20 seconds to answer)\n\nTerm: **" + data[
                                 1] + "**\n\nAnswers:\n:regional_indicator_a:: " + data[0][
                                             0] + "\n:regional_indicator_b:: " + data[0][
                                             1] + "\n:regional_indicator_c:: " +
                                         data[0][2] + "\n:regional_indicator_d:: " + data[0][3], color=0x4257b2)
        embed.set_footer(text="Set ID: " + set_id + " - https://quizlet.com/" + set_id)
        await ctx.delete_last_response()
        prompt = await (await ctx.respond("", embed=embed, components=view.build())).message()
        view.start(prompt)
        await view.wait()  # Wait until the view times out or gets stopped
        if str(bot.d) == "Timeout":
            for i in range(3, 0, -1):
                time.sleep(1)
                await ctx.edit_last_response("*Next question in " + str(i) + " seconds!*")
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
        finalResp = "The last answer was **" + data[2] + "** or answer **" + letter + "**\n> " + "<@" + str(
            bot.d[1]) + "> is " + resp
        await ctx.respond(finalResp + "\n*Next question in 6 seconds!*")
        for i in range(5, 0, -1):
            time.sleep(1)
            await ctx.edit_last_response(finalResp + "\n*Next question in " + str(i) + " seconds!*")
        del remain_quizlet_set[data[2]]
        await ctx.delete_last_response()
    myList = sorted(playerMap.items(), key=lambda x: x[1], reverse=True)
    rank = ""
    for i in range(len(myList)):
        rank += str(i + 1) + ". <@" + str(myList[i][0]) + "> " + str(playerMap[str(myList[i][0])]) + " Points\n"

    embed = hikari.Embed(title="🏆 Rankings 🏆", description=rank, color=0x4257b2)
    embed.set_footer(text="Thanks for playing!")
    await ctx.edit_last_response("", embed=embed, components="")
    gameStarted = False


@bot.command
@lightbulb.add_checks(lightbulb.has_guild_permissions(hikari.Permissions(8)))
@lightbulb.command('reset-bot', '[MUST HAVE ADMIN ACCESS] Resets quizlet bot if errors occur')
@lightbulb.implements(lightbulb.SlashCommand)
async def reset(ctx):
    await ctx.respond("Restarting...")
    global gameStarted
    gameStarted = False
    global int_user_used
    int_user_used = False


miru.load(bot)
bot.run()
