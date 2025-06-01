import pandas as pd
import windrose
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import telebot

try:
    with open("token.txt") as f:
        BOT_TOKEN = f.readline().strip()
except FileNotFoundError:
    print("Файл с токеном не найден!")
    exit()

meteo_bot = telebot.TeleBot(BOT_TOKEN)
user_datasets = {}

def extract_wind_components(data_frame):
    return data_frame['DD'], data_frame['Ff']

def convert_direction_to_degrees(wind_direction):
    if not isinstance(wind_direction, str):
        return np.nan
    
    direction_mapping = {
        "штиль": np.nan,
        "переменное": np.nan,
        "севера": 0.0,
        "северо-северо-востока": 22.5,
        "северо-востока": 45.0,
        "востоко-северо-востока": 67.5,
        "востока": 90.0,
        "востоко-юго-востока": 112.5,
        "юго-востока": 135.0,
        "юго-юго-востока": 157.5,
        "юга": 180.0,
        "юго-юго-запада": 202.5,
        "юго-запада": 225.0,
        "западо-юго-запада": 247.5,
        "запада": 270.0,
        "западо-северо-запада": 292.5,
        "северо-запада": 315.0,
        "северо-северо-запада": 337.5,
    }
    
    normalized_direction = wind_direction.lower().strip()

    for direction, degrees in direction_mapping.items():
        if direction in normalized_direction:
            return degrees
    
    return np.nan

def create_wind_diagram(weather_data):
    calm_count = weather_data['DD'].str.contains('Штиль', na=False).sum()

    directions, speeds = extract_wind_components(weather_data)
    
    wind_angles = [convert_direction_to_degrees(d) for d in directions]
    
    ax = windrose.WindroseAxes.from_ax()
    
    location_info = weather_data.columns[0].split()[2:]
    location_name = " ".join(location_info)
    
    calm_percentage = calm_count / len(speeds) * 100
    
    ax.set_title(
        f"Диаграмма ветров для {location_name}\nДни без ветра: {calm_percentage:.1f}%", 
        pad=25, 
        fontsize=10
    )
    
    ax.bar(
        wind_angles, 
        speeds, 
        normed=True, 
        opening=0.85,
        edgecolor='lightgray', 
        cmap=plt.cm.plasma
    )

    ax.set_xticklabels(['С', 'СВ', 'В', 'ЮВ', 'Ю', 'ЮЗ', 'З', 'СЗ'], fontsize=9)
    ax.set_legend(
        title='Скорость ветра (м/с)', 
        loc='lower center',
        bbox_to_anchor=(0.5, -0.15)
    )
    
    image_buffer = BytesIO()
    plt.savefig(image_buffer, format='png', dpi=100, bbox_inches='tight')
    image_buffer.seek(0)
    plt.close()
    
    return image_buffer


@meteo_bot.message_handler(commands=['start', 'help'])
def send_instructions(message):
    """Отправка инструкций пользователю"""
    greeting = (
        "Добро пожаловать в анализатор метеоданных!\n\n"
        "Для работы отправьте CSV-файл с данными о ветре, "
        "скачанный с сайта RP5.ru (аэропорт Храброво).\n"
        "Файл должен быть в кодировке UTF-8.\n\n"
        "После загрузки файла используйте команду /build_windrose "
        "для генерации диаграммы."
    )
    meteo_bot.reply_to(message, greeting)


@meteo_bot.message_handler(content_types=['document'])
def process_weather_file(message):
    """Обработка метеорологического файла"""
    if not message.document.file_name.lower().endswith('.csv'):
        meteo_bot.reply_to(message, 'Требуется файл в формате CSV.')
        return
    
    try:
        file_info = meteo_bot.get_file(message.document.file_id)
        file_content = meteo_bot.download_file(file_info.file_path)
        
        weather_df = pd.read_csv(
            BytesIO(file_content),
            sep=';',
            skiprows=6,
            encoding='utf-8',
            on_bad_lines='skip'
        )

        if 'DD' not in weather_df or 'Ff' not in weather_df:
            meteo_bot.reply_to(message, "Файл должен содержать колонки 'DD' и 'Ff'")
            return
            
        user_datasets[message.chat.id] = weather_df
        records_count = len(weather_df)
        
        meteo_bot.reply_to(
            message, 
            f"Данные успешно загружены! Записей: {records_count}\n"
            f"Для построения розы ветров используйте /build_windrose"
        )
        
    except Exception as error:
        meteo_bot.reply_to(message, f"Ошибка обработки файла: {str(error)}")


@meteo_bot.message_handler(commands=['build_windrose'])
def generate_wind_chart(message):
    chat_id = message.chat.id
    
    if chat_id not in user_datasets:
        meteo_bot.reply_to(message, "Сначала загрузите CSV-файл с данными!")
        return
        
    try:
        weather_df = user_datasets[chat_id]
        required_cols = ['Ff', 'DD']
        if not all(col in weather_df.columns for col in required_cols):
            meteo_bot.reply_to(message, f"Отсутствуют необходимые колонки: {', '.join(required_cols)}")
            return
            
        meteo_bot.send_chat_action(chat_id, 'upload_photo')
        
        wind_image = create_wind_diagram(weather_df)
        meteo_bot.send_photo(chat_id, wind_image, caption="Диаграмма направлений ветра")
        wind_image.close()
        
    except Exception as error:
        meteo_bot.reply_to(message, f"Ошибка генерации диаграммы: {str(error)}")


if __name__ == '__main__':
    print('==== Сервис анализа ветров запущен ====')
    meteo_bot.infinity_polling()