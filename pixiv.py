import json
import os.path
import shutil
import threading
import traceback
import zipfile
from utils import remove_emojis, filter_file_name, create_gif, config
from logger import logger
from http_client import HttpClient
from config import _HEADERS, _MODE, _LANG, _SEARCH_URL_TYPE, _CONTENT_TYPE, _TYPE, JsonDict, _TYPE_DICT
from sqlite import work_exists, pixiv_id_exists, insert_data, insert_error_data


class Pixiv:
    def __init__(self) -> None:
        self.user_id = _HEADERS["X-User-Id"]
        self.hosts = "https://www.pixiv.net"
        self.http = HttpClient()
        self.http.headers = _HEADERS
        self.version = 'f5f50bb540731f95e7b1eee0509ac311fd4e9525'
        self.root: str = config['Settings']['root']

    def set_proxy(self, proxy_hosts: str = "http://127.0.0.1:1080"):
        self.http.set_proxy(proxy_hosts)
        return self

    def request(self, url: str, method: str = 'GET', **kwargs):
        # TODO 未处理过度使用的情况
        response = self.http.request(url, method, **kwargs)
        return json.loads(response.text, object_hook=JsonDict)
        
    def user_detail(self, user_id: int | str):
        """
        用户详情
        :param user_id: 默认当前登录用户
        :return:
        """
        if not user_id:
            user_id = self.user_id

        url = "%s/ajax/user/%s/profile/top" % (self.hosts, user_id)
        params = {
            "lang": _LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def user_works(self, user_id: int | str, _type: _TYPE = ''):
        """
        用户所有作品
        :param _type: all 全部获取
        :param user_id:
        :return: 返回 插画 illusts 漫画 manga 漫画系列 mangaSeries
        """
        url = "%s/ajax/user/%s/profile/all" % (self.hosts, user_id)
        params = {
            "lang": _LANG,
            "version": self.version,
        }
        resp = self.request(url, "GET", **{'params': params})
        illusts_ids = [_id for _id in resp.body.illusts]
        manga_ids = [_id for _id in resp.body.manga]
        mangaSeries = resp.body.mangaSeries

        def get_all(ids, _type):
            total_length = len(ids)
            batch_size = 48
            # 所有的插画
            works = {}
            for i in range(0, total_length, batch_size):
                batch = ids[i:i + batch_size]
                u = "%s/ajax/user/%s/profile/illusts" % (self.hosts, user_id)
                p = {
                    "ids[]": batch,
                    "work_category": _type,
                    "is_first_page": 0,
                    "lang": 'zh',
                    "version": self.version,
                }

                w = self.request(u, "GET", **{'params': p})
                if not works:
                    works = w.body.works
                else:
                    works.update(w.body.works)

            for work in works.values():
                work.type = _TYPE_DICT[str(work.illustType)]
            return works

        if _type == 'illust':
            return {
                'illusts': get_all(illusts_ids, 'illust'),
                'manga': {},
                'mangaSeries': mangaSeries,
            }
        elif _type == 'manga':
            return {
                'illusts': {},
                'manga': get_all(manga_ids, 'manga'),
                'mangaSeries': mangaSeries
            }
        else:
            return {
                'illusts': get_all(illusts_ids, 'illust'),
                'manga': get_all(manga_ids, 'manga'),
                'mangaSeries': mangaSeries,
            }

    def work_detail(self, illust_id):
        """
        作品详情
        :param illust_id:
        :return:
        """
        url = "%s/ajax/illust/%s" % (self.hosts, illust_id)
        params = {
            "lang": _LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        r.body.type = _TYPE_DICT[str(r.body.illustType)]
        if r.body.pageCount > 1:
            url = '%s/ajax/illust/%s/pages' % (self.hosts, illust_id)
            illusts = self.request(url, "GET", **{'params': params})
            r.body.urls = illusts.body

        return r.body

    def work_follow(self, page: int | str = 1, mode="all"):
        """
        关注用户的新作  https://www.pixiv.net/bookmark_new_illust.php
        :param page: 分页
        :param mode: r18 | all
        :return:
        """
        url = "%s/ajax/follow_latest/illust" % self.hosts
        params = {
            'p': page,
            "mode": mode,
            "lang": _LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def user_bookmark_tags(self):
        url = "%s/ajax/user/%s/illusts/bookmark/tags" % (self.hosts, self.user_id)
        params = {
            "lang": _LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def user_bookmarks_illust(self,
                              tag: str = '',
                              offset: int | str = 0,
                              limit: int | str = 48,
                              restrict="show"
                              ):
        """
        用户收藏作品列表   https://www.pixiv.net/users/xxx/bookmarks/artworks
        :param tag: 从 user_bookmark_tags 获取的收藏标签
        :param offset: 分页偏移
        :param limit: 每页多少
        :param restrict:  show 公开 | hide 不公开
        :return:
        """
        url = "%s/ajax/user/%s/illusts/bookmarks" % (self.hosts, self.user_id)
        params = {
            "tag": tag,
            "offset": offset,
            "limit": limit,
            "rest": restrict,
            "lang": _LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def illust_comments(self, illust_id: int | str, offset: int | str = 0, limit: int | str = 3):
        """
        作品评论
        :param illust_id:
        :param offset:
        :param limit:
        :return:
        """
        url = "%s/ajax/illusts/comments/roots" % self.hosts
        params = {
            "illust_id": illust_id,
            "offset": offset,
            "limit": limit,
            "lang": _LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def recommend_illusts(self, illust_ids: list):
        """
        推荐的作品列表
        :param illust_ids: 18个id [0, 1, 2, ...17]
        :return:
        """
        url = "%s/ajax/illust/recommend/illusts" % self.hosts
        params = {
            "illust_ids[]": illust_ids,
            "lang": _LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def illust_related(self, illust_id: int | str, limit: int | str = 18):
        """
        相关作品列表
        :param illust_id:
        :param limit:
        :return: 接口返回一页相关作品 illusts 和剩下的相关作品id nextIds 剩下的相关作品需要调用 recommend_illusts 获取
        """
        url = "%s/ajax/illust/%s/recommend/init" % (self.hosts, illust_id)
        params = {
            "limit": limit,
            "lang": _LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def illust_ranking(self,
                       mode: _MODE = '',
                       content: _CONTENT_TYPE = '',
                       date: str = '',
                       page: int | str = 1
                       ):
        """
        排行榜  https://www.pixiv.net/ranking.php
        :param mode:
        :param content:
        :param date: demo: 20240615
        :param page:
        :return:
        """
        url = "%s/ranking.php" % self.hosts
        params = {
            "p": page,
            "format": "json",
        }

        if date:
            params["date"] = date
        if content:
            params["content"] = content
        if mode:
            params["mode"] = mode

        r = self.request(url, "GET", **{'params': params})
        return r

    def search_suggestion(self, mode: str = 'all'):
        """
        搜索建议数据
        :param mode:
        :return: myFavoriteTags 喜欢的标签   tagTranslation 标签翻译   recommendTags 人气插画标签
        """
        url = "%s/ajax/search/suggestion" % self.hosts
        params = {
            "mode": mode,
            "lang": _LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def search_user(self, word: str):
        """
        搜索用户 TODO
        :param word:
        :return:
        """
        pass

    def search(self, word: str, url_type: _SEARCH_URL_TYPE = 'artworks', params: dict = None):
        """
        搜索
        :param word: 关键字
        :param url_type:
        :param params: 参数太多了 参考web api
        :return: 返回标签 插画 漫画 小说
        """
        url = "%s/ajax/search/%s/%s" % (self.hosts, url_type, word)
        default_params = {
            "lang": _LANG,
            "version": self.version,
        }

        if params:
            default_params.update(params)

        r = self.request(url, "GET", **{'params': default_params})
        return r.body

    def user_recommends(self,
                        user_id: int | str,
                        user_num: int | str = 20,
                        work_num: int | str = 3,
                        is_r18: bool = True):
        """
        根据某个用户 推荐类似的用户
        :param user_id:
        :param user_num:
        :param work_num:
        :param is_r18:
        :return: thumbnails 作品  recommendUsers 用户对应作品的id  users 推荐的用户
        """
        url = "%s/ajax/user/%s/recommends" % (self.hosts, user_id)
        params = {
            "userNum": user_num,
            "workNum": work_num,
            "isR18": is_r18,
            "lang": _LANG,
            "version": self.version
        }

        r = self.request(url, "get", **{'params': params})
        return r.body

    def user_following(self,
                       offset: int | str = 0,
                       limit: int | str = 24,
                       rest: str = 'show',
                       tag: str = '',
                       accepting_requests=0
                       ):
        """
        已关注的用户
        :param offset:
        :param limit:
        :param rest: hide 非公开 | show 公开
        :param tag:
        :param accepting_requests: 仅显示正在接稿的用户 0 1
        :return:
        """
        url = "%s/ajax/user/%s/following" % (self.hosts, self.user_id)
        params = {
            "offset": offset,
            "limit": limit,
            "rest": rest,
            "tag": tag,
            "acceptingRequests": accepting_requests
        }

        r = self.request(url, "get", **{'params': params})
        return r.body

    def user_follower(self,
                      offset: int | str = 0,
                      limit: int | str = 24,
                      ):
        """
        当前用户粉丝列表
        :param offset:
        :param limit:
        :return:
        """
        url = "%s/ajax/user/%s/followers" % (self.hosts, self.user_id)
        params = {
            "offset": offset,
            "limit": limit,
        }

        r = self.request(url, "get", **{'params': params})
        return r.body

    def user_mypixiv(self,
                     offset: int | str = 0,
                     limit: int | str = 24,
                     ):
        """
        好p友
        :param offset:
        :param limit:
        :return:
        """
        url = "%s/ajax/user/%s/mypixiv" % (self.hosts, self.user_id)
        params = {
            "offset": offset,
            "limit": limit,
        }

        r = self.request(url, "get", **{'params': params})
        return r.body

    def ugoira_metadata(self, illust_id: int | str):
        """
        获取动图的数据
        :param illust_id:
        :return:
        """
        url = "%s/ajax/illust/%s/ugoira_meta" % (self.hosts, illust_id)
        params = {
            "lang": _LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def illust_new(self,
                   lastId: int | str = 0,
                   limit: int | str = 20,
                   type: _TYPE = 'illust',
                   is_r18: bool = False,
                   ):
        """
        大家的新作   https://www.pixiv.net/new_illust.php
        :param lastId:
        :param limit:
        :param type:
        :param is_r18:
        :return:
        """
        url = "%s/ajax/illust/new" % self.hosts
        params = {
            "lastId": lastId,
            "limit": limit,
            "type": type,
            "r18": is_r18,
            "lang": _LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def manga_series(self, serie_id: int | str, page: int | str):
        """
        漫画系列列表  https://www.pixiv.net/user/xxx/series/xxx
        :param serie_id:
        :param page:
        :return:
        """
        url = "%s/ajax/series/%s" % (self.hosts, serie_id)
        params = {
            "p": page,
            "lang": _LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def download(self,
                 urls: str | list,
                 path: str = os.getcwd(),
                 prefix: str = '',
                 fname: str = '',
                 ):
        threads = []
        if isinstance(urls, str):
            urls = [urls]

        for url in urls:
            name = os.path.basename(url)
            if fname:
                if fname.find('.') != -1:
                    name = fname
                else:
                    suffix = os.path.splitext(name)[-1]
                    name = f"{fname}{suffix}"
            if prefix:
                name = f"{prefix}{name}"

            save_path = os.path.join(path, name)
            if os.path.exists(save_path):
                continue

            thread = threading.Thread(target=self.http.download,
                                      args=(url, save_path))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def make_filename(self, illust: dict) -> str:
        if illust.type == 'illust':
            name_rule = config['Settings']['illust_file_name']
        elif illust.type == 'manga':
            if illust.seriesNavData:
                name_rule = config['Settings']['series_manga_file_name']
            else:
                name_rule = config['Settings']['manga_file_name']

    def download_work(self, illust):
        """
        下载作品 必须是 work_detail 返回的数据
        :param illust: work_detail返回的值
        :return:
        """
        title = illust.title
        author = illust.userName
        work_dir = os.path.join(self.root, author)
        if illust.type == 'manga' and illust.seriesNavData:
            work_dir = os.path.join(work_dir, illust.seriesNavData.title)

        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

        logger.info(f"当前作品名称: {title}")
        # 有些系统不支持
        title = remove_emojis(title)
        title = filter_file_name(title)
        if illust.pageCount == 1 and illust.type != 'ugoira':
            if work_exists(illust.id, f"{title}{illust.id}"):
                logger.info(f"插画[{title}]已存在.")
                return
            self.download(illust.urls.original, work_dir, prefix=title)

            if not pixiv_id_exists(illust.id):
                name = os.path.basename(illust.urls.original)
                insert_data(illust.id, f"{title}{name}", illust.userName, illust.userId, illust.type,
                            os.path.join(work_dir, f"{title}{name}"))

            logger.info("单图作品下载完毕.")

        elif illust.pageCount > 1:
            image_urls = [
                page.urls.original
                for page in illust.urls
            ]

            if illust.type == 'manga' and illust.seriesNavData:
                title = f"#{illust.seriesNavData.order} {title}"

            if work_exists(illust.id, f"{title}{illust.id}"):
                logger.info(f"多图[{title}]已存在")

            self.download(image_urls, prefix=title, path=work_dir)

            if not pixiv_id_exists(illust.id):
                name = os.path.basename(image_urls[0])
                insert_data(illust.id, f"{title}{name}", illust.userName, illust.userId, illust.type,
                            os.path.join(work_dir, f"{title}{name}"))

            logger.info("多图作品下载完毕.")
        elif illust.pageCount == 1 and illust.type == 'ugoira':
            logger.info("发现动图开始下载...")
            if work_exists(illust.id, f"{title}{illust.id}"):
                logger.info(f"动图[{title}]已存在")

            ugoira = self.ugoira_metadata(illust.id)
            file_name = illust.title + 'ugoira_tmp.zip'
            extract_path = f"ugoira_tmp{illust.id}"
            self.download(ugoira.originalSrc, fname=file_name)
            f = zipfile.ZipFile(file_name, 'r')
            if not os.path.exists(extract_path):
                os.makedirs(extract_path)

            for file in f.namelist():
                f.extract(file, extract_path)
            f.close()

            save_name = os.path.join(work_dir, f"{title}{illust.id}.gif")
            duration = [item['delay'] / 1000.0 for item in ugoira.frames]
            try:
                create_gif(extract_path, save_name, duration)
            except Exception:
                insert_error_data(ugoira.originalSrc, save_name, str(traceback.format_exc()))
                logger.error(f"生成动图失败,已记录当前数据 \n error: {traceback.format_exc()}")
                shutil.rmtree(extract_path)
                os.remove(file_name)
                return
            shutil.rmtree(extract_path)
            os.remove(file_name)
            if not pixiv_id_exists(illust.id):
                insert_data(illust.id, f"{title}{illust.id}", illust.userName, illust.userId, illust.type,
                            save_name)

            logger.info("动图作品下载完毕.")


if __name__ == '__main__':
    pixiv = Pixiv()
    pixiv.root = '/Users/mac/Desktop/pixiv'
    work = pixiv.work_detail(105191483)
    pixiv.download_work(work)
    # pixiv.make_filename(work)

    # res = pixiv.user_works(22950794)
    # 单个
    # res = pixiv.work_detail(103449028)
    # print(res)
    # 多个图片
    # res = pixiv.work_detail(119467216)
    # res = pixiv.user_detail(22950794)
    # res = pixiv.work_follow(2)
    # res = pixiv.user_bookmarks_illust()
    # res = pixiv.illust_comments(93615998)
    # res = pixiv.illust_related(93615998)
    # res = pixiv.illust_ranking()
    # res = pixiv.search_suggestion()
    # res = pixiv.search('666', params={
    #     "order": "date_d",
    #     "mode": "all",
    #     "p": "1",
    #     "csw": "0",
    #     "s_mode": "s_tag_full",
    #     "type": "all"
    # })

    # res = pixiv.user_recommends(3316400)
    # res = pixiv.user_follower(3316400)
    # res = pixiv.user_following()
    # print(res)
    # pixiv.download(['https://i.pximg.net/img-original/img/2024/06/17/18/24/53/119725660_p0.png'], os.path.join(os.getcwd(), 'test.png'))