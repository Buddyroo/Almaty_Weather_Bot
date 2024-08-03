import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from config import TOKEN, OPENWEATHER_API_KEY, API_OPENAI_KEY
import random
import requests
from datetime import datetime, timedelta
import pytz
import openai
from openai import OpenAI

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализация клиента OpenAI
client = OpenAI(api_key=API_OPENAI_KEY, base_url="https://api.proxyapi.ru/openai/v1")

# Словарь соответствий дней недели
days_of_week = {
    "Monday": "ПОНЕДЕЛЬНИК",
    "Tuesday": "ВТОРНИК",
    "Wednesday": "СРЕДА",
    "Thursday": "ЧЕТВЕРГ",
    "Friday": "ПЯТНИЦА",
    "Saturday": "СУББОТА",
    "Sunday": "ВОСКРЕСЕНЬЕ"
}


# Функция для получения направления ветра
def get_wind_direction(deg):
    directions = [
        "северный", "северо-северо-восточный", "северо-восточный", "восток-северо-восточный",
        "восточный", "восток-юго-восточный", "юго-восточный", "юго-юго-восточный",
        "южный", "юго-юго-западный", "юго-западный", "запад-юго-западный",
        "западный", "запад-северо-западный", "северо-западный", "северо-северо-западный"
    ]
    idx = round(deg / 22.5) % 16
    return directions[idx]


# Функция для получения текущей погоды
def get_current_weather():
    url = f"http://api.openweathermap.org/data/2.5/weather?lat=43.2567&lon=76.9286&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Ошибка получения текущей погоды: {response.status_code}, {response.text}")
        return None
    data = response.json()
    timezone = pytz.timezone('Asia/Almaty')
    weather_info = {
        "temp": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "pressure": data["main"]["pressure"],
        "visibility": data.get("visibility", "N/A"),
        "wind_speed": data["wind"]["speed"],
        "wind_deg": data["wind"]["deg"],
        "wind_direction": get_wind_direction(data["wind"]["deg"]),
        "main": data["weather"][0]["main"],
        "description": data["weather"][0]["description"],
        "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"], tz=timezone).strftime('%H:%M:%S'),
        "sunset": datetime.fromtimestamp(data["sys"]["sunset"], tz=timezone).strftime('%H:%M:%S')
    }
    return weather_info


# Функция для получения прогноза погоды на 5 дней
def get_forecast():
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat=43.2567&lon=76.9286&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Ошибка получения прогноза погоды: {response.status_code}, {response.text}")
        return None
    data = response.json()
    if "list" not in data:
        print(f"Ошибка: ключ 'list' отсутствует в ответе API: {data}")
        return None

    timezone = pytz.timezone('Asia/Almaty')
    forecast = []
    daily_forecast = {}

    for entry in data["list"]:
        dt = datetime.fromtimestamp(entry["dt"], tz=timezone)
        date = dt.date()
        time = dt.strftime('%H:%M')

        if date not in daily_forecast:
            daily_forecast[date] = {
                "temps": [],
                "wind_speeds": [],
                "wind_directions": [],
                "humidity": [],
                "weather": []
            }

        daily_forecast[date]["temps"].append(entry["main"]["temp"])
        daily_forecast[date]["wind_speeds"].append(entry["wind"]["speed"])
        daily_forecast[date]["wind_directions"].append(entry["wind"]["deg"])
        daily_forecast[date]["humidity"].append(entry["main"]["humidity"])
        daily_forecast[date]["weather"].append({
            "time": time,
            "main": entry["weather"][0]["main"],
            "description": entry["weather"][0]["description"]
        })

    for date, values in daily_forecast.items():
        forecast.append({
            "date": date,
            "temp_min": min(values["temps"]),
            "temp_max": max(values["temps"]),
            "humidity": values["humidity"][0],  # Assuming humidity doesn't vary much within a day
            "wind_speed": sum(values["wind_speeds"]) / len(values["wind_speeds"]),
            "wind_direction": get_wind_direction(sum(values["wind_directions"]) / len(values["wind_directions"])),
            "weather": values["weather"]
        })

    return forecast


# Функция для получения ответа от ChatGPT
def question_answer_from_ChatGPT(question):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": question}]
    )

    answer = response.choices[0].message.content

    return answer


@dp.message(Command("photo"))
async def photo(message: Message):
    list_photos = [
        'https://i.pinimg.com/236x/26/b7/14/26b714f32858d685f16d93938545f1b0.jpg',
        'https://i.pinimg.com/736x/00/aa/74/00aa74ebee5b6d90ae8fd89cfd81bd7e.jpg'
    ]
    random_photo = random.choice(list_photos)
    await message.answer_photo(photo=random_photo, caption="Случайное фото")


@dp.message(F.text == "Привет бот")
async def hello(message: Message):
    await message.answer(f"И тебе привет, {message.from_user.full_name}!")


@dp.message(F.photo)
async def photo_react(message: Message):
    answers_list = ['Ого какое фото', 'Классная фотка', 'Ты просто супер', 'Смотрю и радуюсь']
    await message.answer(random.choice(answers_list))


@dp.message(Command("help"))
async def help(message: Message):
    await message.answer(
        "Этот бот умеет выполнять следующие команды:\n/help\n/start\n/photo - фото щенка для настроения\n/weather_now - текущая погода\n/weather_later - погода на следующие 5 дней")


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(f"Привет, {message.from_user.full_name}!")


@dp.message(Command("weather_now"))
async def weather_now(message: Message):
    await message.answer("Давай посмотрим, как в Алматы дела на улице...")
    weather_info = get_current_weather()
    if weather_info is None:
        await message.answer("Не удалось получить текущую погоду.")
        return

    wind_direction = weather_info['wind_direction']
    wind_speed = weather_info['wind_speed']
    wind_deg = weather_info['wind_deg']
    human_readable_wind = f"Ветер дует со скоростью {wind_speed} м/с, направление: {wind_direction}."

    weather_message = (
        f"Текущая температура: {weather_info['temp']}°C\n"
        f"Ощущается как: {weather_info['feels_like']}°C\n"
        f"Влажность: {weather_info['humidity']}%\n"
        f"Давление: {weather_info['pressure']} hPa\n"
        f"Видимость: {weather_info['visibility']} м\n"
        f"{human_readable_wind}\n"
        f"Состояние погоды: {weather_info['main']} - {weather_info['description']}\n"
        f"Время восхода солнца: {weather_info['sunrise']}\n"
        f"Время заката солнца: {weather_info['sunset']}"
    )
    await message.answer(weather_message)

    # Отправка соответствующей картинки в зависимости от состояния погоды
    if weather_info['main'].lower() == 'rain':
        await message.answer_photo(
            'https://rus.azattyq-ruhy.kz/cache/imagine/main_page_full/uploads/news/2024/04/23/66279f48c17de087860562.jpg')
    elif weather_info['main'].lower() == 'clear':
        await message.answer_photo('https://bolzhau.com/uploads/image/2/almaty-weather.jpg')
    elif weather_info['main'].lower() in ['clouds', 'cloudy']:
        await message.answer_photo(
            'https://ru.qaz365.kz/cache/imagine/1200/uploads/news/2024/07/14/6693d41271181600866121.webp')

    # Получение текущего времени
    current_time = datetime.now(pytz.timezone('Asia/Almaty')).strftime('%H:%M')

    await message.answer('Вот такие дела...Дай подумать, что тебе посоветовать 🤔')
    # Формирование запроса для ИИ
    question = f"Погода в Алматы сейчас: {weather_info['description']}. Текущая температура: {weather_info['temp']}°C. Ощущается как: {weather_info['feels_like']}°C. Влажность: {weather_info['humidity']}%. Давление: {weather_info['pressure']} hPa. Видимость: {weather_info['visibility']} м. Ветер: {weather_info['wind_speed']} м/с, направление {wind_direction}. Время: {current_time}. Как лучше одеться мужчине и чем заняться в городе на остаток дня?"

    # Получение ответа от ИИ
    ai_response = question_answer_from_ChatGPT(question)
    await message.answer(ai_response)


@dp.message(Command("weather_later"))
async def weather_later(message: Message):
    await message.answer("Прогноз на следующие 5 дней:")
    forecast = get_forecast()
    if forecast is None:
        await message.answer("Не удалось получить прогноз погоды.")
        return

    today = datetime.now(pytz.timezone('Asia/Almaty')).date()
    headers = ["ЗАВТРА", "ПОСЛЕЗАВТРА", "ЧЕРЕЗ 3 ДНЯ", "ЧЕРЕЗ 4 ДНЯ", "ЧЕРЕЗ 5 ДНЕЙ"]

    for i, day in enumerate(forecast[:5]):
        day_of_week = days_of_week[(today + timedelta(days=i + 1)).strftime('%A')]
        wind_direction = day['wind_direction']
        forecast_message = (
            f"--------{headers[i]}, {day_of_week}--------\n"
            f"Дата: {day['date']}\n"
            f"Максимальная температура: {day['temp_max']}°C\n"
            f"Минимальная температура: {day['temp_min']}°C\n"
            f"Влажность: {day['humidity']}%\n"
            f"Ветер: {day['wind_speed']} м/с, направление: {wind_direction}\n"
            f"Состояние погоды:\n"
        )
        for weather in day['weather']:
            forecast_message += f"  {weather['time']}: {weather['main']} - {weather['description']}\n"
        await message.answer(forecast_message)

    await message.answer(f"Формирую для тебя индивидуальные рекомендации, дай еще раз взглянуть на погоду...👀")
    # Формирование запроса для ИИ для общей рекомендации
    question = f"Прогноз погоды в Алматы на следующие 5 дней:\n"
    for i, day in enumerate(forecast[:5]):
        day_of_week = days_of_week[(today + timedelta(days=i + 1)).strftime('%A')]
        wind_direction = day['wind_direction']
        question += (
            f"{headers[i]}, {day_of_week}: {day['weather'][0]['description']}. "
            f"Максимальная температура: {day['temp_max']}°C, минимальная температура: {day['temp_min']}°C. "
            f"Влажность: {day['humidity']}%. Ветер: {day['wind_speed']} м/с, направление {wind_direction}.\n"
        )
    question += "Какие рекомендации по одежде и чем можно заняться в городе и окрестностях на эти дни?"

    # Получение ответа от ИИ
    ai_response = question_answer_from_ChatGPT(question)

    # Отправка общей рекомендации
    await message.answer(f"Готово! Мои предложения на следующие 5 дней:\n{ai_response}")


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
