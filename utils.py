import configparser
import os
import re
import emoji
from logger import logger
from moviepy.editor import ImageSequenceClip

current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, 'config.ini')
if not os.path.exists(config_path):
    c = configparser.ConfigParser()
    c['User'] = {
        'cookies': '',
        'user_id': ''
    }

    c['Network'] = {
        'use_proxy': '',
        'max_concurrent_threads': '5',
        'stop_max_attempt_number': '2',
        'wait_fixed': '2'
    }

    c['Settings'] = {
        'root': os.getcwd(),
        'db_path': os.path.join(os.getcwd(), 'pixiv.db'),
        'illust_file_name': '{user}/{title}{id}',
        'manga_file_name': '{user}/{title}{id}',
        'series_manga_file_name': '{user}/{series_title}/#{series_order} {title}{id}'
    }

    with open(config_path, 'w') as configfile:
        c.write(configfile)

logger.info('加载配置文件')
config = configparser.RawConfigParser()
config.read(config_path)


def remove_emojis(text):
    # 使用 emoji 库将文本中的表情符号替换为空字符串
    text = emoji.replace_emoji(text, replace=' ')
    return text


def filter_file_name(input_string):
    return re.sub('[\/:*?"<>|]', '-', input_string)


def create_gif(image_folder, output_file, frame_duration=None):
    if frame_duration is None:
        frame_duration = [1]

    logger.info('开始生成gif')
    image_files = [os.path.join(image_folder, img) for img in os.listdir(image_folder)]
    image_files.sort()
    clip = ImageSequenceClip(image_files, durations=frame_duration)
    # clip.write_videofile(output_file, fps=24)
    clip.write_gif(output_file, fps=24)
