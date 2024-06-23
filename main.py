from pixiv import Pixiv

if __name__ == '__main__':
    p = Pixiv()
    # p.set_proxy('http://127.0.0.1:1080')
    # # 获取所有关注的用户的所有作品
    # p.download_user_following()
    # # 清理各种异常的作品
    # p.errors_download()
    # # 订阅关注的用户的最新作品
    # p.subscribing()
    # # 下载用户所有作品
    # p.download_user_works(62286279)
    # # 下载用户收藏的所有作品
    # p.download_user_bookmarks_illust()
    # # 用户搜索
    # p.search_user('666', is_all=True)
    # # 搜索 水着  json_result.illustManga.data
    # json_result = p.search('水着')
    # print(json_result.illustManga.data)
    # # 关注用户的新作
    # result = p.bookmark_new_illust()
    # print(result['thumbnails']['illust'])
    # # 排名榜 今日r18 的插画 每次返回50条 可以使用返回的 'rank_total' 进行分页获取
    # res = p.illust_ranking('daily_r18', 'illust')
    # print(res.contents)
    # # 过取几天的搜索
    # res = p.illust_ranking('daily', 'manga', '20240621')
    # print(res.contents)