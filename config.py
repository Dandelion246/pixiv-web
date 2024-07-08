import configparser
import os
import re
import sys

from logger import logger


class Config:
    config_path = ''
    root = ''
    data: configparser.RawConfigParser = None
    # 并发下载数
    max_concurrent_threads = 5
    # 重试次数
    stop_max_attempt_number = 2
    # 重试间隔时间
    wait_fixed = 2
    headers = {
        "Content-Type": "text/json; charset=utf-8",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6",
        "Referer": "https://www.pixiv.net",
        "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sentry-Trace": "730d6a9c934847f58664931e19674606-8d3bc6248cd52379-0",
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5',
        "Baggage": "sentry-environment=production,sentry-release=f5f50bb540731f95e7b1eee0509ac311fd4e9525,sentry-public_key=7b15ebdd9cf64efb88cfab93783df02a,sentry-trace_id=3e9bb17e86ac4ca78c8d07847d31d949,sentry-sample_rate=0.0001",
        "Cookie": '',
        "X-User-Id": '',
    }

    is_repeat = False

    def __init__(self):
        self.init()
        self.sleep_counter = 0

    def init(self):
        if getattr(sys, 'frozen', False):
            current_dir = os.path.dirname(sys.executable)
        elif __file__:
            current_dir = os.path.dirname(__file__)
        else:
            current_dir = os.getcwd()

        config_path = os.path.join(current_dir, 'config.ini')
        if not os.path.exists(config_path):
            c = configparser.ConfigParser()
            c['User'] = {
                'token': '',
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
                'max_sleep_counter': '120',
                'sleep': '60',
                'is_repeat': 'False',
                'illust_file_name': '{user}/{title}{id}',
                'manga_file_name': '{user}/{title}{id}',
                'series_manga_file_name': '{user}/{series_title}/#{series_order} {title}{id}',
                'skip_user': '',
                'too_many_requests': '200',
                'is_filter_name': 'yes',
            }

            with open(config_path, 'w') as configfile:
                c.write(configfile)

            logger.info(f"配置文件[{config_path}]已生成, 请配置后重些运行.")
            sys.exit()
        self.data = configparser.ConfigParser()
        self.data.read(config_path)
        self.config_path = config_path
        # 并发下载数
        self.max_concurrent_threads = int(self.data['Network']['max_concurrent_threads'])
        # 重试次数
        self.stop_max_attempt_number = int(self.data['Network']['stop_max_attempt_number'])
        # 重试间隔时间
        self.wait_fixed = int(self.data['Network']['wait_fixed'])
        self.root = self.data.get('Settings', 'root')
        self.is_repeat = self.data.getboolean('Settings', 'is_repeat')

    def read(self, key, name):
        self.data = configparser.ConfigParser()
        self.data.read(self.config_path)
        return self.data.get(key, name)

    def modify(self, section, option, value):
        self.data.set(section, option, value)
        with open(self.config_path, 'w') as configfile:
            self.data.write(configfile)

    def add(self, section, option, value):
        if not self.data.has_section(section):
            self.data.add_section(section)
        self.data.set(section, option, value)
        with open(self.config_path, 'w') as configfile:
            self.data.write(configfile)

    def remove(self, section, option):
        if self.data.has_option(section, option):
            self.data.remove_option(section, option)

        with open(self.config_path, 'w') as configfile:
            self.data.write(configfile)


c4g = Config()
if __name__ == '__main__':
    print(bool(c4g.is_repeat))
    # Config.modify('Network', 'use_proxy', 'xxxx')
