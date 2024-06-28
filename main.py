import os
import sys
import time

from logger import logger
from pixiv import Pixiv
from config import MENU_DICT
from sqlite import get_error_count

if __name__ == '__main__':
    p = Pixiv()
    error_count = get_error_count()
    print(f"""注意本脚本只支持从 https://www.pixiv.net/ 网站抓取，其他网站无效。
       _____________________________________________
       mail: q1925186789@gmail.com
       Github: https://github.com/pengRW
       _____________________________________________
       TIP: 当前下载失败的作品数量: {error_count}
       
       [1] 获取所有关注的用户的所有作品
       [2] 订阅关注的用户的最新作品
       [3] 下载用户所有作品
       [4] 下载收藏的所有作品
       [5] 重试下载因各种异常而失败的作品
       [6] Exit
     ___________________________________________________""")
    while True:
        t = input('在键盘中输入菜单选项 [1,2,3,4,5,6]: ')
        if t in ['1', '2', '3', '4', '5', '6']:
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
    if t == '1':
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
