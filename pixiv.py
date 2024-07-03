import json
import shutil
import threading
import time
import traceback
import zipfile
from datetime import datetime

import unicodedata
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt

import config
from config import *
from http_client import HttpClient
from sqlite import work_exists, pixiv_id_exists, insert_data, insert_error_data, query_all_errors, delete_error_by_id
from utils import *


class Pixiv:
    def __init__(self) -> None:
        self.conn = None
        self.user_id = HEADERS["X-User-Id"]
        self.hosts = "https://www.pixiv.net"
        self.http = HttpClient()
        self.http.headers = HEADERS
        self.version = 'f5f50bb540731f95e7b1eee0509ac311fd4e9525'
        self.config_path = init_config()
        logger.info('加载配置文件')
        self.cp = configparser.RawConfigParser()
        self.root: str = self.config('Settings', 'root')
        if not HEADERS['Cookie']:
            logger.error('请配置cookies')
            sys.exit()

        if not HEADERS['X-User-Id']:
            logger.error('请配置user_id')
            sys.exit()

        if not os.path.isdir(self.config('Settings', 'root')):
            logger.error('config.ini Settings->root 目录有问题')
            sys.exit()

    def set_proxy(self, proxy_hosts: str = "http://127.0.0.1:1080"):
        self.http.set_proxy(proxy_hosts)
        return self

    def is_skip_user(self, user_id: int | str) -> bool:
        return str(user_id) in [num.strip() for num in self.config('Settings', 'skip_user').split(',')]

    def make_filename(self, illust: dict, url='') -> str:
        name_rule = ''
        res = ''
        name_dict = {
            'id': os.path.basename(url) if url else '',
            'user': filter_file_name(remove_emojis(illust['userName'])),
            'user_id': illust['userId'],
            'title': filter_file_name(remove_emojis(illust['title'])),
            'page_title': filter_file_name(remove_emojis(illust['alt'])),
            'type': illust['type'],
            'id_num': illust['id'],
            'date': datetime.fromisoformat(illust['createDate']).strftime("%Y-%m-%d"),
            'upload_date': datetime.fromisoformat(illust['uploadDate']).strftime("%Y-%m-%d"),
            'bmk': illust['bookmarkCount'],
            'like': illust['likeCount'],
            'bmk_id': illust['bookmarkData']['id'] if illust['bookmarkData'] else '',
            'view': illust['viewCount'],
            'series_title': illust['seriesNavData']['title'] if illust['seriesNavData'] else '',
            'series_order': illust['seriesNavData']['order'] if illust['seriesNavData'] else '',
            'series_id': illust['seriesNavData']['seriesId'] if illust['seriesNavData'] else '',
            'AI': 'AI' if int(illust['aiType']) == 1 else '',
            'tags': ",".join([item["tag"] for item in illust['tags']['tags']]),
        }

        if illust['type'] in ['illust', 'ugoira']:
            name_rule = self.config('Settings', 'illust_file_name')
            if illust['type'] == 'ugoira':
                name_dict['id'] = f"{name_dict['id_num']}.gif"
        elif illust['type'] == 'manga':
            if illust['seriesNavData']:
                name_rule = self.config('Settings', 'series_manga_file_name')
            else:
                name_rule = self.config('Settings', 'manga_file_name')

        if name_rule:
            res = name_rule.format(**name_dict)

        return res

    def config(self, key, name):
        self.cp.read(self.config_path)
        value = self.cp.get(key, name)
        self.cp.clear()
        return value

    @retry(stop=stop_after_attempt(1))
    def request(self, url: str, method: str = 'GET', **kwargs):
        try:
            response = self.http.request(url, method, **kwargs)
            return json.loads(response.text, object_hook=JsonDict)
        except Exception as e:
            if traceback.format_exc().find('Too Many Requests') != -1:
                logger.info("\npixiv 返回 Too Many Requests 休息200s (￣ρ￣)..zzZZ\n")
                time.sleep(int(self.config('Settings', 'too_many_requests')))

            raise e

    def login(self, email, password):
        # TODO 待完成
        # r = self.http.client.get(
        #     "https://accounts.pixiv.net/login?lang=zh&source=pc&view_type=page&ref=wwwtop_accounts_index",
        # )
        #
        # pattern = re.compile('<input type="hidden" name="post_key" value="(.*?)">', re.S)
        # post_key = re.search(pattern, r.text).group(1)
        data = {
            "pixiv_id": email,
            "password": password,
            "captcha": "",
            "g_recaptcha_response": "",
            "post_key": '885d11c7fa8ec15d7fbc538518ab516a',
            "source": "pc",
            "ref": "wwwtop_accounts_index",
            "return_to": "https://www.pixiv.net/"
        }
        res = self.http.client.post("https://accounts.pixiv.net/api/login?lang=zh",
                                    data=data)
        return res

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
            "lang": LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def user_works(self, user_id: int | str, _type: TYPE = ''):
        """
        用户所有作品
        :param _type: all 全部获取
        :param user_id:
        :return: 返回 插画 illusts 漫画 manga 漫画系列 mangaSeries
        """
        url = "%s/ajax/user/%s/profile/all" % (self.hosts, user_id)
        params = {
            "lang": LANG,
            "version": self.version,
        }
        resp = self.request(url, "GET", **{'params': params})
        illusts_ids = [_id for _id in resp.body.illusts]
        manga_ids = [_id for _id in resp.body.manga]
        manga_series = resp.body.mangaSeries

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
                work.type = TYPE_DICT[str(work.illustType)]
            return works

        if _type == 'illust':
            return {
                'illusts': get_all(illusts_ids, 'illust'),
                'manga': {},
                'mangaSeries': manga_series,
            }
        elif _type == 'manga':
            return {
                'illusts': {},
                'manga': get_all(manga_ids, 'manga'),
                'mangaSeries': manga_series
            }
        else:
            return {
                'illusts': get_all(illusts_ids, 'illust'),
                'manga': get_all(manga_ids, 'manga'),
                'mangaSeries': manga_series,
            }

    def work_detail(self, illust_id):
        """
        作品详情
        :param illust_id:
        :return:
        """
        url = "%s/ajax/illust/%s" % (self.hosts, illust_id)
        params = {
            "lang": LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        r.body.type = TYPE_DICT[str(r.body.illustType)]
        if r.body.pageCount > 1:
            url = '%s/ajax/illust/%s/pages' % (self.hosts, illust_id)
            illusts = self.request(url, "GET", **{'params': params})
            r.body.urls = illusts.body

        return r.body

    def bookmark_new_illust(self, page: int | str = 1, mode="all"):
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
            "lang": LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def user_bookmark_tags(self):
        url = "%s/ajax/user/%s/illusts/bookmark/tags" % (self.hosts, self.user_id)
        params = {
            "lang": LANG,
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
            "lang": LANG,
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
            "lang": LANG,
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
            "lang": LANG,
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
            "lang": LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def illust_ranking(self,
                       mode: MODE = '',
                       content: CONTENT_TYPE = '',
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
            "lang": LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def search_user(self, word: str, page=1, is_all=False, is_same=False):
        """
        搜索用户
        :param word: 搜索的名称
        :param page: 分页
        :param is_all: False 全部  True 投稿作品的用户
        :param is_same: True 完全一致  False 部分一致
        :return:
        """
        url = "%s/search_user.php" % self.hosts
        params = {
            "s_mode": 's_usr',
            'nick': word,
        }

        if is_same:
            params['nick_mf'] = 1

        if page > 1:
            params['p'] = page
            params['comment'] = ''

        if is_all:
            params['i'] = 0

        self.http.headers = {
            'User-Agent': HEADERS['User-Agent'],
            'Cookie': HEADERS['Cookie'],
        }
        html = self.http.request(url, "GET", **{'params': params})
        res = {'users': {}}
        soup = BeautifulSoup(html.text, 'html.parser')
        res['page_total'] = re.search(r'\d+', soup.find('span', class_='count-badge').text).group(0)
        lis = soup.find_all('li', class_='user-recommendation-item')
        for li in lis:
            href = li.find('a').get('href')
            user_id = re.search(r'/users/(\d+)', href).group(1)
            count = 0
            if li.find('dl').find('dd'):
                count = li.find('dl').find('dd').find('a').text
            user = {
                'id': user_id,
                'avatar': li.find('a').get('data-src'),
                'name': li.find('h1').find('a').text,
                'count': count,
                'introduction': li.find('p').text,
                'images': []
            }

            images = {}
            ul = li.find('ul', class_='images')
            if ul:
                arr = ul.find_all('li')
                for v in arr:
                    images['url'] = v.get('data-src')
                    images['count'] = 1
                    div = v.find('div', class_='page-count')
                    if div:
                        images['count'] = div.find('span').text

            res['users'][user_id] = user

        return res

    def search(self, word: str, url_type: SEARCH_URL_TYPE = 'artworks', params: dict = None):
        """
        搜索
        :param word: 关键字
        :param url_type:
        :param params: 参数太多了 参考web api
        :return: 返回标签 插画 漫画 小说
        """
        url = "%s/ajax/search/%s/%s" % (self.hosts, url_type, word)
        default_params = {
            "lang": LANG,
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
            "lang": LANG,
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
            "lang": LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def illust_new(self,
                   last_id: int | str = 0,
                   limit: int | str = 20,
                   _type: TYPE = 'illust',
                   is_r18: bool = False,
                   ):
        """
        大家的新作   https://www.pixiv.net/new_illust.php
        :param last_id:
        :param limit:
        :param _type:
        :param is_r18:
        :return:
        """
        url = "%s/ajax/illust/new" % self.hosts
        params = {
            "lastId": last_id,
            "limit": limit,
            "type": _type,
            "r18": is_r18,
            "lang": LANG,
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
            "lang": LANG,
            "version": self.version,
        }

        r = self.request(url, "GET", **{'params': params})
        return r.body

    def download_work(self, illust):
        """
        下载作品 必须是 work_detail 返回的数据
        :param illust: self.work_detail返回的值
        :return:
        """
        if config.sleep_counter >= int(self.config('Settings', 'max_sleep_counter')):
            logger.info("\n开始休息 (＿ ＿*) Z z z\n")
            time.sleep(int(self.config('Settings', 'sleep')))
            config.sleep_counter = 0

        title = unicodedata.normalize('NFC', illust.title)
        author = unicodedata.normalize('NFC', illust.userName)
        author = author.split('@')[0]
        if self.config('Settings', 'is_filter_name'):
            # 有些系统不支持
            author = remove_emojis(author)
            title = filter_file_name(remove_emojis(title))

        logger.info(f"当前作品名称: {title}")
        if illust.pageCount == 1 and illust.type != 'ugoira':
            config.sleep_counter += 1
            filename = self.make_filename(illust, illust.urls.original)
            save_path = os.path.join(self.root, filename)
            if os.path.exists(save_path):
                logger.info(f"保存位置[{save_path}]已存在")
                return

            name = os.path.basename(save_path)
            path = os.path.dirname(save_path)
            if work_exists(illust.id, os.path.splitext(name)[0]) and not bool(self.config('Settings', 'is_repeat')):
                logger.info(f"插画[{title}]已存在.")
                return

            os.makedirs(path, exist_ok=True)
            self.http.download(illust.urls.original, save_path)
            if not pixiv_id_exists(illust.id):
                insert_data(illust.id, name, author, illust.userId, illust.type, save_path)
            logger.info(f"单图作品下载完毕 saved: {save_path}")
        elif illust.pageCount > 1:
            threads = []
            for url in illust.urls:
                if config.sleep_counter >= int(self.config('Settings', 'max_sleep_counter')):
                    logger.info("\n开始休息 (￣ρ￣)..zzZZ\n")
                    time.sleep(int(self.config('Settings', 'sleep')))
                    config.sleep_counter = 0

                config.sleep_counter += 1
                filename = self.make_filename(illust, url.urls.original)
                save_path = os.path.join(self.root, filename)
                if os.path.exists(save_path):
                    logger.info(f"保存位置[{save_path}]已存在")
                    continue

                name = os.path.basename(save_path)
                if work_exists(illust.id, os.path.splitext(name)[0]) and not bool(self.config('Settings', 'is_repeat')):
                    logger.info(f"多图[{filename}]已存在")
                    continue

                path = os.path.dirname(save_path)
                os.makedirs(path, exist_ok=True)
                if not pixiv_id_exists(illust.id):
                    insert_data(illust.id, name, author, illust.userId, illust.type, save_path)

                thread = threading.Thread(target=self.http.download,
                                          args=(url.urls.original, save_path))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            logger.info(f"多图作品下载完毕.")
        elif illust.pageCount == 1 and illust.type == 'ugoira':
            logger.info("发现动图开始下载...")
            config.sleep_counter += 1
            filename = self.make_filename(illust)
            save_path = os.path.join(self.root, filename)
            if os.path.exists(save_path):
                logger.info(f"保存位置[{save_path}]已存在")
                return

            name = os.path.basename(save_path)
            if work_exists(illust.id, os.path.splitext(name)[0]) and not bool(self.config('Settings', 'is_repeat')):
                logger.info(f"动图[{title}]已存在")
                return

            path = os.path.dirname(save_path)
            os.makedirs(path, exist_ok=True)
            ugoira = self.ugoira_metadata(illust.id)
            tmp_path = os.path.join(os.getcwd(), illust.id + 'ugoira_tmp.zip')
            extract_path = os.path.join(os.getcwd(), f"ugoira_tmp{illust.id}")
            os.makedirs(extract_path, exist_ok=True)
            self.http.download(ugoira.originalSrc, tmp_path)
            f = zipfile.ZipFile(tmp_path, 'r')
            for file in f.namelist():
                f.extract(file, extract_path)
            f.close()

            files = os.listdir(extract_path)
            duration = [item['delay'] / 1000.0 for item in ugoira.frames if item['file'] in files]
            try:
                create_gif(extract_path, save_path, duration)
            except:
                insert_error_data(ugoira.originalSrc, save_path, str(traceback.format_exc()))
                logger.error(f"生成动图失败,已记录当前数据 \n error: {traceback.format_exc()}")
                shutil.rmtree(extract_path)
                os.remove(tmp_path)
                return
            shutil.rmtree(extract_path)
            os.remove(tmp_path)
            if not pixiv_id_exists(illust.id):
                insert_data(illust.id, name, author, illust.userId, illust.type, save_path)

            logger.info(f"动图作品下载完毕 saved: {save_path}")
        else:
            logger.info("这是什么奇怪的文件 (✖﹏✖) 不会下载")

    def errors_download(self):
        """
        重新下载 因为各种异常没有成功下载的作品
        :return:
        """
        errors = query_all_errors()
        for err in errors:
            try:
                if os.path.exists(err[2]):
                    delete_error_by_id(err[0])
                    continue

                url = err[1]
                suffix = os.path.splitext(url)[-1]
                pixiv_id = re.search(r'(\d{5,})', url).group(1)
                if suffix == '.zip':
                    work = self.work_detail(pixiv_id)
                    self.download_work(work)
                else:
                    self.http.download(url, err[2])

                if not pixiv_id_exists(pixiv_id):
                    work = self.work_detail(pixiv_id)
                    insert_data(pixiv_id, work.title, work.userName, work.userId, work.type, err[2])

                delete_error_by_id(err[0])
            except:
                logger.error(traceback.format_exc())
                continue

    def process_works(self, works):
        for illust in works.values():
            title = remove_emojis(illust.title)
            if pixiv_id_exists(illust.id) and not bool(self.config('Settings', 'is_repeat')):
                logger.info(f"[{title}]已存在")
                continue
            try:
                work = self.work_detail(illust.id)
                self.download_work(work)
            except:
                logger.error(traceback.format_exc())
                continue

    def download_user_following(self, start_user: int | str = ''):
        """
        下载关注的所有用户的所有作品
        :param start_user: 可以指定从那个作者开始
        """
        logger.info('开始检查订阅内容')
        # 获取所有关注的用户
        res = self.user_following(0, 24)
        users = res.users
        limit = 24

        for offset in range(24, res.total, limit):
            res = self.user_following(offset, limit)
            users.extend(res.users)

        if start_user:
            index = -1
            for i, item in enumerate(users):
                if isinstance(start_user, int) and int(item.get('userId')) == start_user:
                    index = i
                    break
                if isinstance(start_user, str) and start_user in item.get('userName'):
                    index = i
                    break
            if index != -1:
                users = users[index:]

        for user in users:
            logger.info(f"当前抓取作者: {user.userName}")
            if self.is_skip_user(user.userId):
                logger.info(f"[{user.userId}] 跳过")
                continue

            # 用户所有作品
            self.download_user_works(user.userId)

    def subscribing(self):
        """
        增量更新 从已关注的用户的新作 检查是否有没有下载的作品, 一直检查 直到遇到已下载的数据 才暂停
        :return:
        """
        page = 1
        while True:
            works = self.bookmark_new_illust(page)
            for illust in works['thumbnails']['illust']:
                if self.is_skip_user(illust.userId):
                    logger.info(f"[{illust.userId}] 跳过")
                    continue

                if work_exists(illust.id):
                    logger.info("没有新的作品.")
                    logger.info(f"更新订阅完成.")
                    return

                logger.info(f"发现新作品[{illust.title}], 开始下载...")
                work = self.work_detail(illust.id)
                self.download_work(work)
                logger.info(f"[{illust.title}], 下载完成.")

            page += 1

    def download_user_works(self, user_id):
        """
        下载用户的所有作品
        :param user_id:
        :return:
        """
        works = self.user_works(user_id)
        self.process_works(works['manga'])
        self.process_works(works['illusts'])

    def download_user_bookmarks_illust(self, tag='', restrict='show'):
        first_page = self.user_bookmarks_illust(tag, restrict=restrict)
        works = first_page.works
        limit = 48
        if first_page.total > 0:
            for offset in range(48, first_page.total, limit):
                page = self.user_bookmarks_illust(tag, offset, limit, restrict=restrict)
                works.extend(page.works)

            for work in works:
                detail = self.work_detail(work.id)
                self.download_work(detail)

if __name__ == '__main__':
    pixiv = Pixiv()
    pixiv.work_detail(86130791)
# res = re.search(r'(\d{5,})', 'https://i.pximg.net/img-original/img/2023/02/25/18/19/16/99831005_p67.jpg')
# print(res.group(1))
# pixiv.subscribing()
# pixiv.root = '/Users/mac/Desktop/pixiv'
# work = pixiv.work_detail(115103841)
# pixiv.download_work(work)
# pixiv.make_filename(work)

# res = pixiv.user_works(22950794)
# 单个
# work = pixiv.work_detail(119800855)
# print(res)
# 多个图片
# res = pixiv.work_detail(119467216)
# pixiv.download_work(work)

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
