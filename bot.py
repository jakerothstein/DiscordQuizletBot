import json
import os
import random
import sys
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import hikari
import miru
import lightbulb
import urllib.parse

from selenium.webdriver.common.by import By

CHROMEDRIVER_PATH = "C:\Program Files (x86)\chromedriver.exe"
options = Options()
# options.headless = True
driver = webdriver.Chrome(CHROMEDRIVER_PATH,
                          chrome_options=options)  # Quizlet uses CloudFlare effectively blocking API requests so to get around this you can use selenium
driver.minimize_window()
bot = lightbulb.BotApp(
    token=''  # DISCORD BOT TOKEN
)


def get_quizlet_data(
        set_id):  # Gets quizlet raw data and parses outputs card data in json format and the number of total terms
    url = "https://quizlet.com/webapi/3.4/studiable-item-documents?filters%5BstudiableContainerId%5D=" + str(
        set_id) + "&filters%5BstudiableContainerType%5D=1&perPage=1000&page=1"  # Link to access quizlet data in json form
    driver.get(url)

    data = driver.find_element(By.CSS_SELECTOR, 'pre').get_attribute('innerHTML')

    parsed = json.loads(data)

    try:
        num_cards = parsed['responses'][0]['paging'][
            'total']  # Tests to see if it was able to successfully locate data meaning it was able to receive the json payload otherwise throws error
        parsed_data = parsed['responses'][0]['models']['studiableItem']
        return [parsed_data, num_cards]
    except:
        return "Error"


def get_quizlet_attributes(set_id):  # Gets data from get_quizlet_data() and parses it into a dict of terms and answers
    output = get_quizlet_data(set_id)
    if output == "Error":
        return "Error"
    quizlet_set = {}
    for i in range(output[1]):
        quizlet_set[output[0][i]['cardSides'][0]['media'][0]['plainText']] = output[0][i]['cardSides'][1]['media'][0][
            'plainText']  # json route to parse data
    return quizlet_set


def get_quiz_data(orig_quizlet_set,
                  remain_quizlet_set):  # Gets the orig_quizlet_set to use as possible answers and uses the remain_quizlet_set to randomly select a term and answer returns everything in a list
    ans_options = []
    remain_key_lst = list(remain_quizlet_set.keys())
    answer = random.choice(remain_key_lst)
    prompt = remain_quizlet_set[answer]
    ans_options.append(answer)

    remain_options = list(orig_quizlet_set.keys())
    remain_options.remove(answer)

    while len(ans_options) < 4:
        option = random.choice(remain_options)
        ans_options.append(option)
        remain_options.remove(option)

    random.shuffle(ans_options)  # Scrambles the order of the ans_options
    return [ans_options, prompt, answer]


def correct_letter(data):  # Checks which is the correct letter in ans_options
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


def convert(a):  # Converts a list to a dict
    it = iter(a)
    res_dct = dict(zip(it, it))
    return res_dct


def get_start_players_str(players_lst, user_id):  # Creates the string that will be output to display playerList
    resp = "> Players: "
    for i in range(len(players_lst)):
        if resp.find(str(user_id)) == -1:
            resp += "<@" + players_lst[i] + "> "
    return resp


def get_quizlet_set_name(set_id):
    url = "https://quizlet.com/" + str(set_id)
    driver.get(url)
    data = BeautifulSoup(driver.page_source, "html.parser")

    name = data.find('title').encode_contents()

    return str(name[0:len(name) - 21].decode("utf-8"))


class join_game(miru.View):  # Class for joining game
    players = []

    @miru.button(label="Join", style=hikari.ButtonStyle.SUCCESS)
    async def start_button(self, button: miru.Button, ctx: miru.Context) -> None:
        global int_user_used  # Checks if the user that created the game is in the list of players using global vars
        global init_user

        if not int_user_used:
            int_user_used = True
            join_game.players.append(init_user)

        if str(ctx.user.id) not in join_game.players:  # Checks if that user the submitted the request is not already in the party
            join_game.players.append(
                str(ctx.user.id))  # If True it adds them to the party if not it will tell them that they are already in the party
            resp = get_start_players_str(join_game.players, ctx.user.id)
            await ctx.edit_response(resp)
            bot.d = join_game.players  # Effectively a global var that can be accessed in the function calls
        else:
            await ctx.respond("You have already joined the party!",
                              flags=hikari.MessageFlag.EPHEMERAL)

        # player.append(ctx.user.id)

    @miru.button(label="Start", style=hikari.ButtonStyle.PRIMARY)
    async def stop_button(self, button: miru.Button, ctx: miru.Context):
        global int_user_used  # Checks if the user that created the game is in the list of players using global vars
        global init_user

        if not int_user_used:
            int_user_used = True
            join_game.players.append(init_user)

        if str(ctx.user.id) == str(
                init_user):  # Checks if the user that pressed the button is the person that created the party
            bot.d = join_game.players  # Logs the players in the game
            join_game.players = []  # Clears data in local class var
            self.stop()  # Stop listening for interactions
        else:
            await ctx.respond("You must be the leader of the party in order to start the game!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(label="Leave", style=hikari.ButtonStyle.DANGER)
    async def leave_button(self, button: miru.Button, ctx: miru.Context):
        global int_user_used  # Checks if the user that created the game is in the list of players using global vars
        global init_user

        if not int_user_used:
            int_user_used = True
            join_game.players.append(init_user)

        if str(ctx.user.id) in join_game.players:  # Checks if user is in the party
            join_game.players.remove(str(ctx.user.id))  # Removes user from the party
            resp = get_start_players_str(join_game.players, ctx.user.id)  # Gets string containing party members
            await ctx.edit_response(resp)  # Updates party
            bot.d = join_game.players  # Logs new party
            if init_user not in join_game.players:  # Checks if leader left the party and if so it will end and reset the game
                await ctx.edit_response("> *This game was ended because the leader left the party*", embeds="",
                                        components="")
                bot.d = "Timeout1"  # Key to reset the program but not delete the last message
                self.stop()  # Stops button input

        else:  # If they are not in the party
            await ctx.respond("You can't leave if you are not the party!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(label="Cancel", style=hikari.ButtonStyle.SECONDARY)
    async def cancel_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) == str(init_user):  # Only lets the party leader cancel the game
            bot.d = "Timeout"  # Key to delete last message and restart the game
            global gameStarted  # Resets the game vars as backup
            gameStarted = False
            global int_user_used
            int_user_used = False
            self.stop()  # Stops button input
        else:
            await ctx.respond("You must be the leader of the party to cancel the game",
                              flags=hikari.MessageFlag.EPHEMERAL)

    async def on_timeout(self) -> None:
        bot.d = "Timeout"  # If the user take too long (60 seconds) it will automatically delete the last message and restart the game


class answers(miru.View):
    @miru.button(emoji=hikari.Emoji.parse("🇦"),
                 style=hikari.ButtonStyle.PRIMARY)  # A, B, C and D buttons are all the same but output different outputs (A, B, C, D) and also the user ID who clicked the button
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

    @miru.button(emoji=hikari.Emoji.parse("🛑"),
                 style=hikari.ButtonStyle.DANGER)  # Stop button stops the game and goes directly to the winners page
    async def stop_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) in playerMap:  # Checks if the player is in the game
            if str(ctx.user.id) == str(init_user):  # Only party leader (creator) can end the game
                bot.d = ["Stop", ctx.user.id]
                global gameStarted
                gameStarted = False
                global int_user_used
                int_user_used = False
                self.stop()
            else:
                await ctx.respond("You must be the party leader (creator) to end the game!",
                                  flags=hikari.MessageFlag.EPHEMERAL)
        else:
            await ctx.respond("You are not part of this game. Join a game next round!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    async def on_timeout(self) -> None:  # If the question times out (20 seconds) it will call a function to tick down
        bot.d = "Timeout"


playerMap = {}  # The following vars are all global vars controlled by quizlet_game() to communicate the miru commands

gameStarted = False

init_user = ""

int_user_used = False

rand_url = ""


@bot.command
@lightbulb.option('url', 'Quizlet set url', type=str)  # Requires a string input with the slash command
@lightbulb.command('start-game', 'Starts quizlet game')  # Command titles
@lightbulb.implements(lightbulb.SlashCommand)
async def quizlet_game(ctx: lightbulb.SlashContext):
    global gameStarted
    global rand_url
    if gameStarted:  # Checks if there is already a game in progress and if so it will terminate the func
        await ctx.respond("There is already a game in progress!", flags=hikari.MessageFlag.EPHEMERAL)
        time.sleep(1)
        rand_url = ""
        return
    global int_user_used  # Inits the global vars
    int_user_used = False
    global init_user
    init_user = str(ctx.author.id)
    await (await ctx.respond("Starting Game...")).message()
    gameStarted = True  # Locks game so other instances can not be run
    view = join_game(timeout=60)  # after 60 seconds the menu will disappear
    if rand_url == "":
        url = str(ctx.options.url)  # Gets url from the slash command
    else:
        url = rand_url
    # set_id = re.sub("[^0-9]", "", url)
    try:
        parsed = urllib.parse.urlsplit(url)  # Parses the url to get the set_id num
        set_id = parsed.path.split("/")[1]
    except:
        gameStarted = False
        await ctx.edit_last_response(
            "> **Invalid set url**\nPlease check your url\nExample formatting: https://quizlet.com/set_id/quizlet-set-name/")
        rand_url = ""
        return
    if not set_id.isdigit():
        set_id = parsed.path.split("/")[2]

    orig_quizlet_set = get_quizlet_attributes(
        set_id)  # Uses the set ID to call functions to return a dict of all the terms and answers

    if orig_quizlet_set == "Error":  # Error handling
        gameStarted = False
        await ctx.edit_last_response(
            "> **Invalid set url**\nPlease check your url\nExample formatting: https://quizlet.com/set_id/quizlet-set-name/")
        rand_url = ""
        return
    remain_quizlet_set = {}
    remain_quizlet_set.update(orig_quizlet_set)
    if len(orig_quizlet_set) < 4:
        await ctx.edit_last_response(
            "> *The quizlet set has an insufficient amount of cards.*\n*Please use another set*")
        gameStarted = False
        rand_url = ""
        return
    set_name = get_quizlet_set_name(set_id)
    embed = hikari.Embed(title="Quizlet Bot", description="**Game Started!**\nSet Name: " + str(
        set_name) + "\n*Press Join to enter the party*",
                         # Embedding
                         color=0x4257b2, url="https://github.com/jakerothstein/DiscordQuizletBot")
    embed.set_thumbnail("https://www.aisd.net/wp-content/files/quizlet.png")  # Random quizlet image from online
    embed.set_footer(text="Set ID: " + set_id + " - https://quizlet.com/" + set_id)

    message_str = "> Players: <@" + str(ctx.author.id) + ">"
    message = await ctx.edit_last_response(message_str, embed=embed,
                                           components=view.build())  # Builds and sends message
    view.start(message)  # Listens for a response from the buttons
    await view.wait()  # Wait until the view times out or a self.stop() is triggered in the buttons
    if str(bot.d) == "Timeout":  # Timeout handling from buttons
        await ctx.delete_last_response()
        gameStarted = False  # Resets the game vars
        rand_url = ""
        return
    elif str(bot.d) == "Timeout1":  # Timeout1 handling from buttons
        gameStarted = False
        rand_url = ""
        return
    playerList = bot.d  # If not errors gets player data from bot.d
    del bot.d  # Deletes bot data to reset list
    for player in range(len(playerList)):
        playerList.insert(playerList.index(playerList[player]) * 2 + 1,
                          0)  # Formats playerList[] to create a playerMap{} to hold scores
    global playerMap
    playerMap = convert(playerList)  # Converts to dict
    del playerList  # Resets var
    round_cnt = 0  # Round counter var
    stop = True  # While loop condition
    while stop:
        view = answers(timeout=20)  # Answers only last for 20 sec
        data = get_quiz_data(orig_quizlet_set, remain_quizlet_set)  # Gets formatted quiz data
        round_cnt += 1
        embed = hikari.Embed(title="Round " + str(round_cnt) + "/" + str(len(orig_quizlet_set)),
                             description="Match the terms (20 seconds to answer)\n\nTerm: **" + data[  # Embedded
                                 1] + "**\n\nAnswers:\n:regional_indicator_a:: " + data[0][
                                             0] + "\n:regional_indicator_b:: " + data[0][
                                             1] + "\n:regional_indicator_c:: " +
                                         data[0][2] + "\n:regional_indicator_d:: " + data[0][3], color=0x4257b2)
        embed.set_footer(text="Set ID: " + set_id + " - https://quizlet.com/" + set_id)
        await ctx.delete_last_response()  # Deletes last message
        prompt = await (await ctx.respond("", embed=embed,
                                          components=view.build())).message()  # Sends new message to go to bottom of the channel
        view.start(prompt)  # Starts listening
        await view.wait()  # Wait until the view times out or gets stopped
        if str(bot.d) == "Timeout":  # Timeout handling if no one responds in 20 sec
            for i in range(3, 0, -1):
                time.sleep(1)
                await ctx.edit_last_response("*Next question in " + str(i) + " seconds!*")
            continue  # Goes to next question
        if str(bot.d[0]) == "Stop":  # Checks if game is over and if so ends the loop
            stop = False
            continue
        letter = correct_letter(data)  # Finds the correct answer
        if str(bot.d[0]) == letter:  # If correct
            playerMap[str(bot.d[1])] += 10  # Add 10 points
            resp = "correct :white_check_mark:\n> Good job " + "<@" + str(bot.d[1]) + ">\n> You have " + str(
                playerMap[str(bot.d[1])]) + " points!"
        else:
            playerMap[str(bot.d[1])] -= 10  # Subtract 10 points
            resp = "incorrect :x:\n> <@" + str(bot.d[1]) + "> answered: " + str(bot.d[0]) + "\n> You have " + str(
                playerMap[str(bot.d[1])]) + " points."
        finalResp = "The last answer was **" + data[2] + "** or answer **" + letter + "**\n> " + "<@" + str(
            bot.d[1]) + "> is " + resp
        if len(remain_quizlet_set) < 2:
            stop = False
            continue
        await ctx.respond(finalResp + "\n*Next question in 6 seconds!*")  # Countdown till next question
        for i in range(5, 0, -1):
            time.sleep(1)
            await ctx.edit_last_response(finalResp + "\n*Next question in " + str(i) + " seconds!*")
        del remain_quizlet_set[data[2]]  # Removes used question from remain_quizlet_set
        await ctx.delete_last_response()
    myList = sorted(playerMap.items(), key=lambda x: x[1], reverse=True)  # If game is over sort the players
    rank = ""
    for i in range(len(myList)):
        rank += str(i + 1) + ". <@" + str(myList[i][0]) + "> " + str(
            playerMap[str(myList[i][0])]) + " Points\n"  # Adds the players to the scoreboard

    embed = hikari.Embed(title="🏆 Rankings 🏆", description=rank, color=0x4257b2)  # Embed
    embed.set_footer(text="Thanks for playing!")
    await ctx.edit_last_response("", embed=embed, components="")
    gameStarted = False  # Stops game
    rand_url = ""
    return 1


@bot.command
@lightbulb.option('key', 'The key used to search for a set', type=str)  # Requires a string input with the slash command
@lightbulb.command('search-game', 'Starts a random game with a user provided key')
@lightbulb.implements(lightbulb.SlashCommand)
async def rand_quizlet_game(ctx: lightbulb.SlashContext):
    url = "https://quizlet.com/search?query=" + str(ctx.options.key).replace(" ", "+") + "&type=sets"
    driver.get(url)
    data = BeautifulSoup(driver.page_source, "html.parser")
    div_data = data.find('div', attrs={'class': 'SetPreviewCard-header'})
    target_url = div_data.find('a')['href']
    global rand_url
    rand_url = str(target_url)
    await quizlet_game(ctx)


@bot.command
@lightbulb.add_checks(lightbulb.has_guild_permissions(hikari.Permissions(8)))  # Checks for admin and resets vars
@lightbulb.command('reset-bot', '[MUST HAVE ADMIN ACCESS] Resets quizlet bot if errors occur')
@lightbulb.implements(lightbulb.SlashCommand)
async def reset(ctx):
    await ctx.respond("Restarting...")
    try:
        driver.quit()
    except:
        print("Webdriver does not exist")
    await ctx.edit_last_response("Reset Complete ✅")
    os.execv(sys.executable, ['python'] + sys.argv)

miru.load(bot)
bot.run()
