from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
import json
import asyncio
from typing import List, Union
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
import os

FILE_NAME = "base.json"
MODEL_LIST = {}

TOKEN = os.environ.get("tgbot_token")

storage = MemoryStorage()

bot = Bot(TOKEN_beta)
dp = Dispatcher(bot, storage=storage)


class AlbumMiddleware(BaseMiddleware):
    album_data: dict = {}

    def __init__(self, latency: Union[int, float] = 0.01):
        self.latency = latency
        super().__init__()

    async def on_process_message(self, message: types.Message, data: dict):
        if not message.media_group_id:
            self.album_data[message.from_user.id] = [message]

            message.conf["is_last"] = True
            data["album"] = self.album_data[message.from_user.id]
            await asyncio.sleep(self.latency)
        else:
            try:
                self.album_data[message.media_group_id].append(message)
                raise CancelHandler()
            except KeyError:
                self.album_data[message.media_group_id] = [message]
                await asyncio.sleep(self.latency)

                message.conf["is_last"] = True
                data["album"] = self.album_data[message.media_group_id]

    async def on_post_process_message(self, message: types.Message, result: dict, data: dict):
        if not message.media_group_id:
            if message.from_user.id and message.conf.get("is_last"):
                del self.album_data[message.from_user.id]
        else:
            if message.media_group_id and message.conf.get("is_last"):
                del self.album_data[message.media_group_id]


def get_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('/start'))

    return kb


def get_choose() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('Возврат средств')).insert(
        KeyboardButton('Другая проблема'))


def get_cancel() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Закончить работу')).insert(
        KeyboardButton('↪️ Назад'))


def get_phone() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Закончить работу')).insert(
        KeyboardButton('↪️ Назад')).add(KeyboardButton("Отправить свой номер телефона ☎️", request_contact=True))


def update_base():
    global FILE_NAME, MODEL_LIST
    with open(FILE_NAME, "r", encoding="utf-8") as file:
        MODEL_LIST = json.loads(file.read())


update_base()


class ClientStatesGroup(StatesGroup):
    hello = State()

    descr = State()
    model = State()
    phone = State()
    bill = State()
    passing = State()

    another_problem = State()
    phone_problem = State()

@dp.message_handler(Text(equals="❌ Закончить работу"), state='*')
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    await message.reply('Действия отменены. Чтобы начать работу нажмите кнопку <b>/start</b>',
                        reply_markup=get_keyboard(), parse_mode="HTML")
    await state.finish()


@dp.message_handler(Text(equals="↪️ Назад"), state='*')
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    string_current_state = str(current_state).split(":")[1]
    if string_current_state == "model":
        await ClientStatesGroup.descr.set()
        await message.reply('Вы вернулись на предыдущий шаг. Представьтесь и опишите проблему.',
                            reply_markup=get_cancel())
    if string_current_state == "bill":
        await ClientStatesGroup.phone.set()
        await message.reply('Вы вернулись на предыдущий шаг. Отправьте номер телефона по кнопке в меню чата.',
                            reply_markup=get_phone())
    if string_current_state == "phone":
        await ClientStatesGroup.model.set()
        await message.reply('Вы вернулись на предыдущий шаг. Введите модель аппарата.')
    if string_current_state == "descr":
        await ClientStatesGroup.hello.set()
        await message.reply('Вы вернулись на предыдущий шаг. Выберите проблему, нажав на соответствующую кнопку.',
                            reply_markup=get_choose())
    if string_current_state == "another_problem":
        await ClientStatesGroup.hello.set()
        await message.reply('Вы вернулись на предыдущий шаг. Выберите проблему, нажав на соответствующую кнопку.',
                            reply_markup=get_choose())
    if string_current_state == "phone_problem":
        await ClientStatesGroup.another_problem.set()
        await message.reply('Вы вернулись на предыдущий шаг. Представьтесь и опишите проблему.',
                            reply_markup=get_choose())

@dp.message_handler(commands=['start'])
async def preproc(message: types.Message) -> None:
    await ClientStatesGroup.hello.set()
    await message.answer(text="Выберите проблему, нажав на соответствующую кнопку.", reply_markup=get_choose())


@dp.message_handler(Text(equals="Другая проблема"), state=ClientStatesGroup.hello)
async def other_problems(message: types.Message) -> None:
    await ClientStatesGroup.another_problem.set()
    await message.answer(
        text=f"Приносим извинения за предоставленные неудобства, напишите как вас зовут и опишите возникшую проблему.",
        reply_markup=get_cancel())


@dp.message_handler(content_types=["text"], state=ClientStatesGroup.another_problem)
async def other_problem_descr_handle(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["another_problem"] = message.text
    await ClientStatesGroup.phone_problem.set()
    await message.reply("Отправьте свой номер телефона (по кнопке в меню чата).", reply_markup=get_phone())


@dp.message_handler(content_types=["text", "contact"], state=ClientStatesGroup.phone_problem)
async def other_problem_phone_handler(message: types.Message, state: FSMContext):
    id_to_forward = ###
    mention = "(Отсутствует)"
    if message.from_user.mention:
        mention = message.from_user.mention

    if message.contact is not None:
        async with state.proxy() as data:
            data["phone_problem"] = message.contact.phone_number
        await message.reply(
            "Вы успешно отправили свой номер телефона.\nСпасибо за предоставленную информацию, в ближайшее время с вами свяжется оператор для возврата средств.",
            reply_markup=get_keyboard())
        text_to_forward = "Описание: " + data[
            "another_problem"] + "\n" + "Никнейм пользователя: " + mention + "\n" + "Профиль пользователя: " + message.from_user.url + "\n" + "Номер телефона пользователя: " + data["phone_problem"]
        await bot.send_message(chat_id=id_to_forward, text=text_to_forward)
        await state.finish()
    else:
        await message.reply("Неправильно введён номер телефона, повторите попытку.")


@dp.message_handler(Text(equals="Возврат средств"), state=ClientStatesGroup.hello)
async def start(message: types.Message) -> None:
    await ClientStatesGroup.descr.set()
    await message.answer(
        text=f"Приносим извинения за предоставленные неудобства, напишите как вас зовут и опишите возникшую проблему.",
        reply_markup=get_cancel())


@dp.message_handler(content_types=["text"], state=ClientStatesGroup.descr)
async def descr_handle(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["descr"] = message.text
    await ClientStatesGroup.next()
    await message.reply(" Приятно познакомиться. Напишите номер аппарата <b>большими русскими буквами</b>.",
                        reply_markup=get_cancel(), parse_mode="HTML")


@dp.message_handler(content_types=["text"], state=ClientStatesGroup.model)
async def model_handle(message: types.Message, state: FSMContext):
    global MODEL_LIST
    async with state.proxy() as data:
        data["model"] = message.text
    if data["model"] in MODEL_LIST["coffee_pot"]:
        await ClientStatesGroup.phone.set()
        await message.reply("Отправьте свой номер телефона (по кнопке в меню чата).", reply_markup=get_phone())
    elif data["model"] in MODEL_LIST["snack_pot"]:
        await state.finish()
        await message.reply(
            "Вам не о чем беспокоиться, аппарат осуществляет возврат средств автоматически в течении 24 часов.",
            reply_markup=get_keyboard())
    else:
        await message.reply("Такой модели нет. Введите другую модель.")


@dp.message_handler(lambda message: not message.photo, state=ClientStatesGroup.bill)
async def check_photo(message: types.Message):
    await message.reply("Отправьте медиафайл (фотографию или видео).")


@dp.message_handler(content_types=["text", "contact"], state=ClientStatesGroup.phone)
async def phone_handler(message: types.Message, state: FSMContext):
    if message.contact is not None:
        await ClientStatesGroup.bill.set()
        async with state.proxy() as data:
            data["phone"] = message.contact.phone_number
        await message.reply(
            "Вы успешно отправили свой номер телефона.\nСпасибо за предоставленную информацию. Отправьте в чат фото транзакции, и фото или видео фиксацию неисправности оборудования.",
            reply_markup=get_cancel())
    else:
        await message.reply("Неправильно введён номер телефона, повторите попытку.")


@dp.message_handler(content_types=['video', 'photo'], state=ClientStatesGroup.bill)
async def handle_albums(message: types.Message, album: List[types.Message], state: FSMContext):
    id_to_forward = ###
    mention = "(Отсутствует)"
    if message.from_user.mention:
        mention = message.from_user.mention

    if not message.media_group_id:
        if message.photo:
            async with state.proxy() as data:
                await bot.send_photo(chat_id=id_to_forward, photo=message.photo[-1].file_id,
                                     caption="Описание: " + data["descr"] + "\n" + "Указанная модель: " + data[
                                         "model"] + "\n" "Никнейм пользователя: " + mention + "\n" + "Профиль пользователя: " + message.from_user.url + "\n" + "Номер телефона пользователя: " +
                                             data["phone"])
                await message.reply("В ближайшее время с вами свяжется оператор для возврата средств.",
                                    reply_markup=get_keyboard())
            await state.finish()
        else:
            await bot.send_message(message.chat.id, text="Отправьте медиафайл (фотографию или видео).")
    else:
        media_group = types.MediaGroup()
        for obj in album:
            if obj.photo:
                file_id = obj.photo[-1].file_id
                async with state.proxy() as data:
                    caption = "Описание: " + data["descr"] + "\n" + "Указанная модель: " + data[
                        "model"] + "\n" "Никнейм пользователя: " + mention + "\n" + "Профиль пользователя: " + message.from_user.url + "\n" + "Номер телефона пользователя: " + \
                              data["phone"]
            else:
                file_id = obj[obj.content_type].file_id
            try:
                media_group.attach({"media": file_id, "type": obj.content_type})
                media_group.media[0]["caption"] = caption
            except ValueError:
                return await message.answer("Этот тип не поддерживается aiogram.")

        await bot.send_media_group(chat_id=id_to_forward, media=media_group)
        await message.reply("В ближайшее время с вами свяжется оператор для возврата средств.",
                            reply_markup=get_keyboard())
        await state.finish()


if __name__ == "__main__":
    dp.middleware.setup(AlbumMiddleware())
    executor.start_polling(dp, skip_updates=True)
