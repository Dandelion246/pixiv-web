import os
import re
import time
from datetime import datetime

import emoji
import unicodedata
from config import c4g
from logger import logger
from moviepy.editor import ImageSequenceClip


def remove_emojis(text):
    # 使用 emoji 库将文本中的表情符号替换为空字符串
    text = emoji.replace_emoji(text, replace='')
    if len(text) == 0:
        text = '0emoji'
    return text


def filter_file_name(input_string):
    def replace_char(char):
        if char in r'\\:*?"<>|':  # 使用反斜杠来转义反斜杠本身
            return '-'
        elif char == '/' and ord(char) == 0x002F:  # 标准斜杠
            return '-'
        return char

    return (''.join(replace_char(char) for char in input_string)).strip()


def create_gif(image_folder, output_file, frame_duration=None):
    if frame_duration is None:
        frame_duration = [0.1] * len(os.listdir(image_folder))

    logger.info('开始生成gif')
    image_files = [os.path.join(image_folder, img) for img in os.listdir(image_folder)]
    image_files.sort()
    try:
        clip = ImageSequenceClip(image_files, durations=frame_duration)
        # clip.write_videofile(output_file, fps=24)
        clip.write_gif(output_file, fps=12)
    except:
        logger.error('动图生成失败, 开始默认方案.')
        from PIL import Image
        images = [Image.open(file) for file in image_files]
        images[0].save(output_file, save_all=True, append_images=images[1:], duration=100, loop=0)


def is_skip_user(user_id: int | str) -> bool:
    return str(user_id) in [num.strip() for num in c4g.read('Settings', 'skip_user').split(',')]


def make_filename(illust: dict, url='') -> str:
    name_rule = ''
    res = ''
    name_dict = {
        'id': os.path.basename(url) if url else '',
        'user': unicodedata.normalize('NFC', filter_file_name(remove_emojis(illust['userName']))),
        'user_id': illust['userId'],
        'title': unicodedata.normalize('NFC', filter_file_name(remove_emojis(illust['title']))),
        'page_title': unicodedata.normalize('NFC', filter_file_name(remove_emojis(illust['alt']))),
        'type': illust['type'],
        'id_num': illust['id'],
        'date': datetime.fromisoformat(illust['createDate']).strftime("%Y-%m-%d"),
        'upload_date': datetime.fromisoformat(illust['uploadDate']).strftime("%Y-%m-%d"),
        'bmk': illust['bookmarkCount'],
        'like': illust['likeCount'],
        'bmk_id': illust['bookmarkData']['id'] if illust['bookmarkData'] else '',
        'view': illust['viewCount'],
        'series_title': unicodedata.normalize('NFC', filter_file_name(remove_emojis(illust['seriesNavData']['title']))) if illust['seriesNavData'] else '',
        'series_order': illust['seriesNavData']['order'] if illust['seriesNavData'] else '',
        'series_id': illust['seriesNavData']['seriesId'] if illust['seriesNavData'] else '',
        'AI': 'AI' if int(illust['aiType']) == 1 else '',
        'tags': ",".join([item["tag"] for item in illust['tags']['tags']]),
    }

    if illust['type'] in ['illust', 'ugoira']:
        name_rule = c4g.read('Settings', 'illust_file_name')
        if illust['type'] == 'ugoira':
            name_dict['id'] = f"{name_dict['id_num']}.gif"
    elif illust['type'] == 'manga':
        if illust['seriesNavData']:
            name_rule = c4g.read('Settings', 'series_manga_file_name')
        else:
            name_rule = c4g.read('Settings', 'manga_file_name')

    if name_rule:
        res = name_rule.format(**name_dict)

    return res


def is_sleep():
    if c4g.sleep_counter >= int(c4g.read('Settings', 'max_sleep_counter')):
        logger.info("\n开始休息 (￣ρ￣)..zzZZ\n")
        time.sleep(int(c4g.read('Settings', 'sleep')))
        c4g.sleep_counter = 0


def is_url(string):
    url_pattern = re.compile(
        r'^(https?|ftp)://'  # 协议部分
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # 域名部分
        r'localhost|'  # 本地主机
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # 或者 IPv4 地址
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # 或者 IPv6 地址
        r'(?::\d+)?'  # 端口号（可选）
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)  # 路径部分
    return re.match(url_pattern, string) is not None


if __name__ == '__main__':
    res = filter_file_name('PICKUP GIRL COMIC ')
    print(res)
