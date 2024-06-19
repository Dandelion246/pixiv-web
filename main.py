import os
import time

from logger import logger
from pixiv import Pixiv
from sqlite import work_exists
from utils import config, remove_emojis

if __name__ == '__main__':
    p = Pixiv()
    logger.info('开始检查订阅内容')
    sleep = 20

    # 获取所有关注的用户
    res = p.user_following()
    users = res.users[14:]
    limit = 24
    for offset in range(24, res.total, limit):
        res = p.user_following(offset, limit)
        users.extend(res.users)

    for user in users:
        # 用户所有作品
        json_result = p.user_works(user.userId)
        for illust in json_result['manga'].values():
            title = remove_emojis(illust.title)
            if work_exists(illust.id, f"{title}{illust.id}"):
                logger.info(f"[{title}]已存在")
                continue

            work = p.work_detail(illust.id)
            p.download_work(work)

        logger.info(f"manga下载完毕, 休息{sleep}秒.")
        time.sleep(sleep)

        for illust in json_result['illusts'].values():
            title = remove_emojis(illust.title)
            if work_exists(illust.id, f"{title}{illust.id}"):
                logger.info(f"[{title}]已存在")
                continue

            work = p.work_detail(illust.id)
            p.download_work(work)

        time.sleep(sleep)
        logger.info(f"插画下载完毕, 休息{sleep}秒.")
