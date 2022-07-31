import json
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


class MyView(miru.View):
    @miru.button(label="Join", style=hikari.ButtonStyle.SUCCESS)
    async def rock_button(self, button: miru.Button, ctx: miru.Context) -> None:
        await ctx.respond("<@" + str(ctx.user.id) + ">" + " joined")
        # player.append(ctx.user.id)

    @miru.button(label="Start", style=hikari.ButtonStyle.DANGER)
    async def stop_button(self, button: miru.Button, ctx: miru.Context):
        self.stop()  # Stop listening for interactions


@bot.command
@lightbulb.option('url', 'Quizlet set url', type=str)
@lightbulb.command('start-game', 'Starts quizlet game')
@lightbulb.implements(lightbulb.SlashCommand)
async def pic(ctx: lightbulb.SlashContext):
    msg = await (await ctx.respond("Starting Game...")).message()
    players = []
    view = MyView(timeout=60)

    url = ctx.options.url
    set_id = re.sub("[^0-9]", "", url)
    quizlet_set = get_quizlet_attributes(set_id)
    quizlet_set_quiz = quizlet_set

    embed = hikari.Embed(title="Quizlet Bot", description="**Game Started!**\n*Press Join to enter the game*",
                         color=0x4257b2, url=url)
    embed.set_thumbnail("https://www.aisd.net/wp-content/files/quizlet.png")
    embed.set_footer(text="Set ID: " + set_id)

    message = await ctx.edit_last_response("", embed=embed, components=view.build())
    view.start(message)
    await view.wait()  # Wait until the view times out or gets stopped
    await msg.respond("The game is starting!")



miru.load(bot)
bot.run()
