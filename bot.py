from selenium import webdriver
from selenium.webdriver.chrome.options import Options

CHROMEDRIVER_PATH = "C:\Program Files (x86)\chromedriver.exe"
options = Options()
options.headless = True
driver = webdriver.Chrome(CHROMEDRIVER_PATH, chrome_options=options)


url = "https://quizlet.com/webapi/3.4/studiable-item-documents?filters%5BstudiableContainerId%5D=680671080&filters%5BstudiableContainerType%5D=1&perPage=1000&page=1"
driver.get(url)

data = driver.page_source

driver.close()

print(data)