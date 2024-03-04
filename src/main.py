import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

from config import driver_path, TOKEN_API, snake_triggers, alter_triggers, game_trigger, CHAT_ID_TO_SEND

from aiogram import Bot, Dispatcher, types, executor

def prepare_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=driver, options=options)
    driver.maximize_window()
    return driver

bot = Bot(token=TOKEN_API)
dp = Dispatcher(bot=bot)

class Room:
    def __init__(self, name):
        self.name = name
        self.driver_ = prepare_driver()

    def get_driver(self):
        return self.driver_

    def get_name(self):
        return self.name

def process_sequence(seq):
    if len(seq) <= 1: return False
    alter_cnt, snake_cnt = 1, 1
    for i in range(1, len(seq)):
        if seq[i] == seq[i - 1]:
            snake_cnt += 1
            alter_cnt = 1
        else:
            alter_cnt += 1
            snake_cnt = 1
    if alter_cnt in alter_triggers or snake_cnt in snake_triggers:
        return True
    return False

rooms = []  # Список объектов комнат

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await bot.send_message(chat_id=CHAT_ID_TO_SEND, text="По завершению открытия комнаты введите <All done> в терминал.\n")
    while True:
        name = input("Введите название комнаты и после этого в открывшемся окне ChromeDriver перейдите на нее: ")
        if name != "All done": rooms.append(Room(name))
        else: break
    while True:
        for room in rooms:
            await parse_room(room)


async def parse_room(room):
    try:
        driver = room.get_driver()
        outer_iframe = driver.find_element(By.TAG_NAME, 'iframe')
        driver.switch_to.frame(outer_iframe)
        inner_iframe = driver.find_element(By.TAG_NAME, 'iframe')
        driver.switch_to.frame(inner_iframe)
        outer_svgs = driver.find_elements(By.CSS_SELECTOR, 'svg[data-type="coordinates"]')

        try:
            game_counter = int(driver.find_element(By.CSS_SELECTOR, '[data-role="gameCount"]').text)
            print(f"Games passed in room {room.get_name()}: {game_counter}")
            if game_counter <= game_trigger:
                checker, seq = 0, []
                for outer_svg in outer_svgs:
                    x, y = float(outer_svg.get_attribute('x')), float(outer_svg.get_attribute('y'))
                    if (x, y) == (0.05, 0.05): checker += 1
                    if checker == 2: break
                    inner_svg = outer_svg.find_element(By.CSS_SELECTOR, 'svg[data-type="roadItem"]')
                    fill_value = inner_svg.find_element(By.CSS_SELECTOR, 'g[data-type="roadItemColor"]').get_attribute('fill')
                    if not 0.045 <= x - int(x) <= 0.055 or not 0.045 <= y - int(y) <= 0.055: break
                    if fill_value == "#2E83FF": seq.append('B')
                    if fill_value == "#EC2024": seq.append('R')
                    print(f"x: {x}, y: {y}, color: {fill_value}")
                if process_sequence(seq):
                    await bot.send_message(chat_id=CHAT_ID_TO_SEND, text=f"{room.get_name()}")
        except Exception: pass
        driver.switch_to.default_content()
    except Exception:
        await bot.send_message(chat_id=CHAT_ID_TO_SEND, text=f"Необходим перезапуск комнаты {room.get_name()}")

if __name__ == "__main__":
    executor.start_polling(dp)
