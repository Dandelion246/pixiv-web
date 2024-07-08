import os
import re
import sys
import threading
import time

from logger import logger
from pixiv import Pixiv
from const import MENU_DICT
from config import c4g
from sqlite import get_error_count
from utils import is_url


def init():
    c4g.init()
    if not c4g.read('User', 'token'):
        ok = input('请先登录, 是否跳转到登录界面(y|n)?')
        if ok == 'y':
            import webview

            def login_monitor():
                while True:
                    current_url = window.get_current_url()
                    if current_url.find('accounts.pixiv.net') != -1:
                        time.sleep(1)
                        continue

                    cookies = ';'.join([cookie.output(attrs=[], header="") for cookie in window.get_cookies()])
                    pattern = r"PHPSESSID=([^;]+)"
                    match = re.search(pattern, cookies)
                    if not match:
                        res = window.create_confirmation_dialog('Question', '登录失败了, 需要重试吗?')
                        if res:
                            window.load_url(
                                'https://accounts.pixiv.net/login?return_to=https%3A%2F%2Fwww.pixiv.net%2F&lang=zh&source=pc&view_type=page')
                        else:
                            window.destroy()
                    else:
                        c4g.modify('User', 'token', match.group(1))
                        window.destroy()

                    break

            window = webview.create_window('Woah dude!',
                                           'https://accounts.pixiv.net/login?return_to=https%3A%2F%2Fwww.pixiv.net%2F&lang=zh&source=pc&view_type=page',
                                           width=1000, height=900,
                                           )
            thread = threading.Thread(target=login_monitor)
            thread.start()
            webview.start()
        else:
            sys.exit()


if __name__ == '__main__':
    init()
    p = Pixiv()
    error_count = get_error_count()
    print(f"""注意本脚本只支持从 https://www.pixiv.net/ 网站抓取，其他网站无效。
_____________________________________________
mail: q1925186789@gmail.com
Github: https://github.com/pengRW
_____________________________________________
TIP: 当前下载失败的作品数量: {error_count}

[0] 下载作品
[1] 获取所有关注的用户的所有作品
[2] 订阅关注的用户的最新作品
[3] 下载用户所有作品
[4] 下载收藏的所有作品
[5] 重试下载因各种异常而失败的作品
[6] Exit
___________________________________________________""")
    while True:
        while True:
            t = input('在键盘中输入菜单选项 [0,1,2,3,4,5,6]: ')
            if t in ['0', '1', '2', '3', '4', '5', '6']:
                break

        if t == '6':
            print('感谢使用！')
            time.sleep(1)
            sys.exit()

        if sys.platform == 'win32':
            os.system('cls')
        else:
            os.system('clear')

        logger.debug(f'当前模式：{MENU_DICT[t]}')
        logger.debug(f'根目录：{p.root}')
        if t == '0':
            work_id = 0
            while 1:
                value = input('请输入要抓取的作品ID或者URL：')
                if value.isdigit():
                    work_id = value
                    break

                if is_url(value):
                    work_id = value.split('/')[-1]
                    break

            p.work_detail(work_id).download()
        elif t == '1':
            user = input('可以指定从哪个作者开始(ID或者名称)：')
            if user:
                logger.debug(f'开始从[{user}]开始下载...')

            p.download_user_following(user)
        elif t == '2':
            logger.debug('开始增量更新...')
            p.subscribing()
        elif t == '3':
            while 1:
                user_id = input('请输入要抓取的作者ID：')
                if user_id.isdigit():
                    break

            p.download_user_works(user_id)
        elif t == '4':
            logger.debug('开始抓取用户收藏的所有作品...')
            p.download_user_bookmarks_illust()
        elif t == '5':
            logger.debug('开始重试错误作品...')
            p.errors_download()
