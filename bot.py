import asyncio
import json
import os
import random
import sys
import threading
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import hikari
import miru
import lightbulb
import urllib.parse

options = Options()
# options.headless = True
options.add_argument('log-level=3')
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),
                          # https://pypi.org/project/webdriver-manager/
                          options=options)  # Quizlet uses CloudFlare effectively blocking API requests so to get around this you can use selenium
with open('key.txt', 'r') as file:
    token = file.read()

driver.minimize_window()
bot = lightbulb.BotApp(
    token=str(token),  # DISCORD BOT TOKEN
    banner=None  # No intro console banner
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
        try:  # Checks for an image
            img = output[0][i]['cardSides'][1]['media'][1]['url']
        except:
            img = ""
        quizlet_set[output[0][i]['cardSides'][0]['media'][0]['plainText']] = [output[0][i]['cardSides'][1]['media'][0][
                                                                                  'plainText'],
                                                                              img]  # json route to parse data
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
    def __init__(self, init_user):
        super().__init__(timeout=60)
        self.players = []
        self.init_user = init_user
        self.int_user_used = False
        self.answer = ""

    @miru.button(label="Join", style=hikari.ButtonStyle.SUCCESS)
    async def start_button(self, button: miru.Button, ctx: miru.Context) -> None:

        if not self.int_user_used:
            self.int_user_used = True
            self.players.append(self.init_user)

        if str(ctx.user.id) not in self.players:  # Checks if that user the submitted the request is not already in the party
            self.players.append(
                str(ctx.user.id))  # If True it adds them to the party if not it will tell them that they are already in the party
            resp = get_start_players_str(self.players, ctx.user.id)
            await ctx.edit_response(resp)
            self.answer = self.players  # Effectively a global var that can be accessed in the function calls
        else:
            await ctx.respond("You have already joined the party!",
                              flags=hikari.MessageFlag.EPHEMERAL)

        # player.append(ctx.user.id)

    @miru.button(label="Start", style=hikari.ButtonStyle.PRIMARY)
    async def stop_button(self, button: miru.Button, ctx: miru.Context):
        if not self.int_user_used:
            self.int_user_used = True
            self.players.append(self.init_user)

        if str(ctx.user.id) == str(
                self.init_user):  # Checks if the user that pressed the button is the person that created the party
            self.answer = self.players  # Logs the players in the game
            self.players = []  # Clears data in local class var
            self.stop()  # Stop listening for interactions
        else:
            await ctx.respond("You must be the leader of the party in order to start the game!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(label="Leave", style=hikari.ButtonStyle.DANGER)
    async def leave_button(self, button: miru.Button, ctx: miru.Context):
        if not self.int_user_used:
            self.int_user_used = True
            self.players.append(self.init_user)

        if str(ctx.user.id) in self.players:  # Checks if user is in the party
            self.players.remove(str(ctx.user.id))  # Removes user from the party
            resp = get_start_players_str(self.players, ctx.user.id)  # Gets string containing party members
            await ctx.edit_response(resp)  # Updates party
            self.answer = self.players  # Logs new party
            if self.init_user not in self.players:  # Checks if leader left the party and if so it will end and reset the game
                await ctx.edit_response("> *This game was ended because the leader left the party*", embeds="",
                                        components="")
                self.answer = "Timeout1"  # Key to reset the program but not delete the last message
                self.stop()  # Stops button input

        else:  # If they are not in the party
            await ctx.respond("You can't leave if you are not the party!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(label="Cancel", style=hikari.ButtonStyle.SECONDARY)
    async def cancel_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) == str(self.init_user):  # Only lets the party leader cancel the game
            self.answer = "Timeout"  # Key to delete last message and restart the game
            self.int_user_used = False
            self.stop()  # Stops button input
        else:
            await ctx.respond("You must be the leader of the party to cancel the game",
                              flags=hikari.MessageFlag.EPHEMERAL)

    async def on_timeout(self) -> None:
        self.answer = "Timeout"  # If the user take too long (60 seconds) it will automatically delete the last message and restart the game


class answers(miru.View):
    def __init__(self, playerMap, init_user):
        super().__init__(timeout=60)
        self.init_user = init_user
        self.playerMap = playerMap
        self.answer = ""

    @miru.button(emoji=hikari.Emoji.parse("🇦"),
                 style=hikari.ButtonStyle.PRIMARY)  # A, B, C and D buttons are all the same but output different outputs (A, B, C, D) and also the user ID who clicked the button
    async def a_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) in self.playerMap:
            self.answer = ["A", ctx.user.id]
            self.stop()
        else:
            await ctx.respond("You are not part of this game. Join a game next round!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji=hikari.Emoji.parse("🇧"), style=hikari.ButtonStyle.PRIMARY)
    async def b_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) in self.playerMap:
            self.answer = ["B", ctx.user.id]
            self.stop()
        else:
            await ctx.respond("You are not part of this game. Join a game next round!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji=hikari.Emoji.parse("🇨"), style=hikari.ButtonStyle.PRIMARY)
    async def c_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) in self.playerMap:
            self.answer = ["C", ctx.user.id]
            self.stop()
        else:
            await ctx.respond("You are not part of this game. Join a game next round!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji=hikari.Emoji.parse("🇩"), style=hikari.ButtonStyle.PRIMARY)
    async def d_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) in self.playerMap:
            self.answer = ["D", ctx.user.id]
            self.stop()
        else:
            await ctx.respond("You are not part of this game. Join a game next round!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji=hikari.Emoji.parse("🛑"),
                 style=hikari.ButtonStyle.DANGER)  # Stop button stops the game and goes directly to the winners page
    async def stop_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if str(ctx.user.id) in self.playerMap:  # Checks if the player is in the game
            if str(ctx.user.id) == str(self.init_user):  # Only party leader (creator) can end the game
                self.answer = ["Stop", ctx.user.id]
                self.stop()
            else:
                await ctx.respond("You must be the party leader (creator) to end the game!",
                                  flags=hikari.MessageFlag.EPHEMERAL)
        else:
            await ctx.respond("You are not part of this game. Join a game next round!",
                              flags=hikari.MessageFlag.EPHEMERAL)

    async def on_timeout(self) -> None:  # If the question times out (20 seconds) it will call a function to tick down
        self.answer = "Timeout"


class quizletGame:

    def __init__(self, ctx, input_type):
        self.playerMap = {}  # The following vars are all global vars controlled by quizlet_game() to communicate the miru commands
        self.init_user = ""
        self.rand_url = ""
        self.ctx = ctx
        self.input_type = input_type

    async def start(self):
        global channel_list
        if str(self.input_type) == 'search':
            url = "https://quizlet.com/search?query=" + str(self.ctx.options.search).replace(" ", "+") + "&type=sets"
            driver.get(url)
            data = BeautifulSoup(driver.page_source, "html.parser")
            try:
                div_data = data.find('div', attrs={'class': 'SetPreviewCard-header'})
                target_url = div_data.find('a')['href']
            except:
                await self.ctx.respond("> Set not found\nPlease search again for another set",
                                       flags=hikari.MessageFlag.EPHEMERAL)
                channel_list.remove(self.ctx.channel_id)
                return
            self.rand_url = str(target_url)
        return await self.quizlet_game()

    async def quizlet_game(self):
        self.init_user = str(self.ctx.author.id)
        await (await self.ctx.respond("Starting Game...")).message()
        view = join_game(self.init_user)  # after 60 seconds the menu will disappear
        if self.rand_url == "":
            url = str(self.ctx.options.url)  # Gets url from the slash command
        else:
            url = self.rand_url
        # set_id = re.sub("[^0-9]", "", url)
        try:
            parsed = urllib.parse.urlsplit(url)  # Parses the url to get the set_id num
            set_id = parsed.path.split("/")[1]
        except:
            await self.ctx.edit_last_response(
                "> **Invalid set url**\nPlease check your url\nExample formatting: https://quizlet.com/set_id/quizlet-set-name/")
            self.rand_url = ""
            channel_list.remove(self.ctx.channel_id)
            return
        if not set_id.isdigit():
            set_id = parsed.path.split("/")[2]

        orig_quizlet_set = get_quizlet_attributes(
            set_id)  # Uses the set ID to call functions to return a dict of all the terms and answers

        if orig_quizlet_set == "Error":  # Error handling
            await self.ctx.edit_last_response(
                "> **Invalid set url**\nPlease check your url\nExample formatting: https://quizlet.com/set_id/quizlet-set-name/")
            rand_url = ""
            channel_list.remove(self.ctx.channel_id)
            return
        remain_quizlet_set = {}
        remain_quizlet_set.update(orig_quizlet_set)
        if len(orig_quizlet_set) < 4:
            await self.ctx.edit_last_response(
                "> *The quizlet set has an insufficient amount of cards.*\n*Please use another set*")
            self.rand_url = ""
            channel_list.remove(self.ctx.channel_id)
            return
        set_name = get_quizlet_set_name(set_id)
        embed = hikari.Embed(title="Quizlet Bot", description="**Game Started!**\nSet Name: " + str(
            set_name) + "\n*Press Join to enter the party*",
                             # Embedding
                             color=0x4257b2, url="https://github.com/jakerothstein/DiscordQuizletBot")
        embed.set_thumbnail("https://www.aisd.net/wp-content/files/quizlet.png")  # Random quizlet image from online
        embed.set_footer(text="Set ID: " + set_id + " - https://quizlet.com/" + set_id)

        message_str = "> Players: <@" + str(self.ctx.author.id) + ">"
        message = await self.ctx.edit_last_response(message_str, embed=embed,
                                                    components=view.build())  # Builds and sends message
        view.start(message)  # Listens for a response from the buttons
        await view.wait()  # Wait until the view times out or a self.stop() is triggered in the buttons
        if str(view.answer) == "Timeout":  # Timeout handling from buttons
            await self.ctx.delete_last_response()
            self.rand_url = ""
            channel_list.remove(self.ctx.channel_id)
            return
        elif str(view.answer) == "Timeout1":  # Timeout1 handling from buttons
            self.rand_url = ""
            channel_list.remove(self.ctx.channel_id)
            return
        playerList = view.answer  # If not errors gets player data from view.answer
        del view.answer  # Deletes bot data to reset list
        for player in range(len(playerList)):
            playerList.insert(playerList.index(playerList[player]) * 2 + 1,
                              0)  # Formats playerList[] to create a playerMap{} to hold scores
        self.playerMap = convert(playerList)  # Converts to dict
        del playerList  # Resets var
        round_cnt = 0  # Round counter var
        stop = True  # While loop condition
        while stop:
            view = answers(self.playerMap, self.init_user)  # Answers only last for 20 sec
            data = get_quiz_data(orig_quizlet_set, remain_quizlet_set)  # Gets formatted quiz data
            round_cnt += 1
            description = "Match the terms (20 seconds to answer)\n\nTerm: **" + data[
                1][0] + "**\n\nAnswers:\n:regional_indicator_a:: " + data[0][
                              0] + "\n:regional_indicator_b:: " + data[0][
                              1] + "\n:regional_indicator_c:: " + data[0][2] + "\n:regional_indicator_d:: " + data[0][3]

            embed = hikari.Embed(title="Round " + str(round_cnt) + "/" + str(len(orig_quizlet_set)),
                                 description=description, color=0x4257b2)
            if data[1][1] != '':
                embed.set_image(data[1][1])
            embed.set_footer(text="Set ID: " + set_id + " - https://quizlet.com/" + set_id)
            await self.ctx.delete_last_response()  # Deletes last message
            prompt = await (await self.ctx.respond("", embed=embed,
                                                   components=view.build())).message()  # Sends new message to go to bottom of the channel
            view.start(prompt)  # Starts listening
            await view.wait()  # Wait until the view times out or gets stopped
            if str(view.answer) == "Timeout":  # Timeout handling if no one responds in 20 sec
                if len(remain_quizlet_set) < 2:
                    stop = False
                    continue
                del remain_quizlet_set[data[2]]
                for i in range(3, 0, -1):
                    time.sleep(1)
                    await self.ctx.edit_last_response("*Next question in " + str(i) + " seconds!*")
                continue  # Goes to next question
            if str(view.answer[0]) == "Stop":  # Checks if game is over and if so ends the loop
                stop = False
                continue
            letter = correct_letter(data)  # Finds the correct answer
            if str(view.answer[0]) == letter:  # If correct
                self.playerMap[str(view.answer[1])] += 10  # Add 10 points
                resp = "correct :white_check_mark:\n> Good job " + "<@" + str(view.answer[1]) + ">\n> You have " + str(
                    self.playerMap[str(view.answer[1])]) + " points!"
            else:
                self.playerMap[str(view.answer[1])] -= 10  # Subtract 10 points
                resp = "incorrect :x:\n> <@" + str(view.answer[1]) + "> answered: " + str(
                    view.answer[0]) + "\n> You have " + str(
                    self.playerMap[str(view.answer[1])]) + " points."
            finalResp = "The last answer was **" + data[2] + "** or answer **" + letter + "**\n> " + "<@" + str(
                view.answer[1]) + "> is " + resp
            if len(remain_quizlet_set) < 2:
                stop = False
                continue
            await self.ctx.respond(finalResp + "\n*Next question in 6 seconds!*")  # Countdown till next question
            for i in range(5, 0, -1):
                time.sleep(1)
                await self.ctx.edit_last_response(finalResp + "\n*Next question in " + str(i) + " seconds!*")
            del remain_quizlet_set[data[2]]  # Removes used question from remain_quizlet_set
            await self.ctx.delete_last_response()
        myList = sorted(self.playerMap.items(), key=lambda x: x[1],
                        reverse=True)  # If game is over sort the players
        rank = ""
        for i in range(len(myList)):
            rank += str(i + 1) + ". <@" + str(myList[i][0]) + "> " + str(
                self.playerMap[str(myList[i][0])]) + " Points\n"  # Adds the players to the scoreboard

        embed = hikari.Embed(title="🏆 Rankings 🏆", description=rank, color=0x4257b2)  # Embed
        embed.set_footer(text="Thanks for playing!")
        await self.ctx.edit_last_response("", embed=embed, components="")
        self.rand_url = ""
        channel_list.remove(self.ctx.channel_id)
        return 1


channel_list = []


@bot.command
@lightbulb.option('url', 'Quizlet set url', type=str)  # Requires a string input with the slash command
@lightbulb.command('start-game', 'Starts quizlet game')  # Command titles
@lightbulb.implements(lightbulb.SlashCommand)
async def url_quizlet_game(ctx: lightbulb.SlashContext):
    channel_id = ctx.channel_id
    global channel_list
    if channel_id not in channel_list:
        channel_list.append(channel_id)
        game = quizletGame(ctx, 'url')
        await game.start()
    else:
        await ctx.respond(
            "> There is already a game running in this channel.\nTry starting a new game in another channel!",
            flags=hikari.MessageFlag.EPHEMERAL)


@bot.command
@lightbulb.option('search', 'Search for your desired set (Calculus BC, Biology, etc.)',
                  type=str)  # Requires a string input with the slash command
@lightbulb.command('search-game', 'Starts a random game with a user provided query')
@lightbulb.implements(lightbulb.SlashCommand)
async def search_quizlet_game(ctx: lightbulb.SlashContext):
    channel_id = ctx.channel_id
    global channel_list
    if channel_id not in channel_list:
        channel_list.append(channel_id)
        game = quizletGame(ctx, 'search')
        await game.start()
    else:
        await ctx.respond(
            "> There is already a game running in this channel.\nTry starting a new game in another channel!",
            flags=hikari.MessageFlag.EPHEMERAL)


@bot.command
@lightbulb.command('info', 'How to use bot')
@lightbulb.implements(lightbulb.SlashCommand)
async def start_rand_quizlet_game(ctx: lightbulb.SlashContext):
    await ctx.respond("This is how you use the bot")  # TODO: Update this with an embed


# @bot.command
# @lightbulb.add_checks(lightbulb.has_guild_permissions(hikari.Permissions(8)))  # Checks for admin and resets vars
# @lightbulb.command('reset-bot', '[MUST HAVE ADMIN ACCESS] Resets quizlet bot if errors occur')
# @lightbulb.implements(lightbulb.SlashCommand)
# async def reset(ctx):
#     await ctx.respond("Restarting...")
#     try:
#         driver.quit()
#     except:
#         print("Webdriver does not exist")
#     await ctx.edit_last_response("Reset Complete ✅")
#     os.execv(sys.executable, ['python'] + sys.argv)


def main():
    miru.load(bot)
    bot.run()


if __name__ == "__main__":
    main()
