import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from config import TOKEN, OPENWEATHER_API_KEY
import random
import requests
from datetime import datetime, timedelta
import pytz

bot = Bot(token=TOKEN)
dp = Dispatcher()


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


# Функция для получения прогноза погоды на 4 дня
def get_forecast():
    url = f"http://pro.openweathermap.org/data/2.5/forecast/hourly?lat=43.2567&lon=76.9286&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    response = requests.get(url)
    data = response.json()
    timezone = pytz.timezone('Asia/Almaty')

    forecast = []
    current_date = None
    daily_forecast = {"temps": [], "wind_speeds": [], "wind_directions": [], "humidity": []}

    for entry in data["list"]:
        date = datetime.fromtimestamp(entry["dt"], tz=timezone).date()
        if current_date is None:
            current_date = date

        if date != current_date:
            forecast.append({
                "date": current_date,
                "temp_min": min(daily_forecast["temps"]),
                "temp_max": max(daily_forecast["temps"]),
                "humidity": daily_forecast["humidity"][0],
                "wind_speed": sum(daily_forecast["wind_speeds"]) / len(daily_forecast["wind_speeds"]),
                "wind_direction": get_wind_direction(
                    sum(daily_forecast["wind_directions"]) / len(daily_forecast["wind_directions"])),
                "main": daily_forecast["main"],
                "description": daily_forecast["description"]
            })
            current_date = date
            daily_forecast = {"temps": [], "wind_speeds": [], "wind_directions": [], "humidity": []}

        daily_forecast["temps"].append(entry["main"]["temp"])
        daily_forecast["wind_speeds"].append(entry["wind"]["speed"])
        daily_forecast["wind_directions"].append(entry["wind"]["deg"])
        daily_forecast["humidity"].append(entry["main"]["humidity"])
        daily_forecast["main"] = entry["weather"][0]["main"]
        daily_forecast["description"] = entry["weather"][0]["description"]

    if daily_forecast["temps"]:
        forecast.append({
            "date": current_date,
            "temp_min": min(daily_forecast["temps"]),
            "temp_max": max(daily_forecast["temps"]),
            "humidity": daily_forecast["humidity"][0],
            "wind_speed": sum(daily_forecast["wind_speeds"]) / len(daily_forecast["wind_speeds"]),
            "wind_direction": get_wind_direction(
                sum(daily_forecast["wind_directions"]) / len(daily_forecast["wind_directions"])),
            "main": daily_forecast["main"],
            "description": daily_forecast["description"]
        })

    return forecast


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
        "Этот бот умеет выполнять следующие команды:\n/help\n/start\n/photo\n/weather_now\n/weather_later")


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(f"Привет, {message.from_user.full_name}!")


@dp.message(Command("weather_now"))
async def weather_now(message: Message):
    await message.answer("Давай посмотрим, как в Алматы дела на улице...")
    weather_info = get_current_weather()
    wind_direction = weather_info['wind_direction']
    wind_speed = weather_info['wind_speed']
    wind_deg = weather_info['wind_deg']
    human_readable_wind = f"Ветер дует со скоростью {wind_speed} м/с с {wind_direction} направления (примерно {wind_deg}°)."

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


@dp.message(Command("weather_later"))
async def weather_later(message: Message):
    await message.answer("Прогноз на следующие 4 дня:")
    forecast = get_forecast()
    forecast_message = ""
    for day in forecast:
        wind_direction = get_wind_direction(day['wind_deg'])
        forecast_message += (
            f"\nДата: {day['date']}\n"
            f"Максимальная температура: {day['temp_max']}°C\n"
            f"Минимальная температура: {day['temp_min']}°C\n"
            f"Влажность: {day['humidity']}%\n"
            f"Ветер: {day['wind_speed']} м/с, направление {wind_direction}\n"
            f"Состояние погоды: {day['main']} - {day['description']}\n"
        )
    await message.answer(forecast_message)


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
