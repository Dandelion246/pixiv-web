import os
import sys
import threading
import time
import cloudscraper
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception
from logger import logger
from config import c4g
from sqlite import insert_error_data
import traceback

thread_semaphore = threading.Semaphore(c4g.max_concurrent_threads)


def failure_function(retry_state):
    url = retry_state.args[1]
    sava_path = retry_state.args[2]
    last_exception = retry_state.outcome.exception() if retry_state.outcome else None
    err = ''
    if last_exception:
        err = ''.join(traceback.format_exception(type(last_exception), value=last_exception,
                                                                 tb=last_exception.__traceback__))

    insert_error_data(url, sava_path, err)


def should_retry(retry_state):
    # 检查最近一次调用是否失败
    response = retry_state.response
    if response is not None and response.status_code == 401:
        logger.error('401错误不重试')
        return False

    return True


class HttpClient:
    def __init__(self, headers=None, proxies=None):
        self.proxies = proxies
        self.headers = headers
        self.client = cloudscraper.create_scraper()

    def set_proxy(self, url='http://localhost:1080'):
        self.proxies = {
            'http': url,
            'https': url
        }

        return self

    @retry(stop=stop_after_attempt(c4g.stop_max_attempt_number),
           wait=wait_fixed(c4g.wait_fixed),
           retry=retry_if_exception(should_retry)
           )
    def request(self, url: str, method: str = 'GET', **kwargs) -> requests.Response:
        """
        发送http请求
        :param url:
        :param method:
        :param kwargs: demo : **{'json': xxx, 'headers': xxx}
        :return: requests.Response
        """
        try:
            if self.headers:
                kwargs.update({"headers": self.headers})

            response = getattr(self.client, method.lower())(url, proxies=self.proxies, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            logger.error(f"request 出现异常, 准备重试 Error:{e}")
            raise e

    @retry(stop=stop_after_attempt(c4g.stop_max_attempt_number),
           wait=wait_fixed(c4g.wait_fixed),
           retry_error_callback=failure_function
           )
    def download(self, download_url: str, save_path: str):
        """
        从 download_url 下载 保存为 save_path
        :param download_url:
        :param save_path: 例子： /Users/mac/Desktop/pixiv/xxx.zip
        :return:
        """
        try:
            thread_semaphore.acquire()
            resp = self.request(download_url, 'get', **{'stream': True})
            total_size = int(resp.headers.get('content-length', 0))
            block_size = 1024  # 1 KB
            start_time = time.time()
            downloaded_size = 0
            c4g.sleep_counter += 1
            if total_size == 0:
                c4g.sleep_counter += 20
                raise Exception(f"{download_url}: total_size = 0")

            total_mb = total_size / (1024 * 1024)
            file_name = os.path.basename(save_path)
            # 写入文件并显示下载进度和速度
            with open(save_path, 'wb') as file:
                for data in resp.iter_content(block_size):
                    downloaded_size += len(data)
                    file.write(data)
                    elapsed_time = time.time() - start_time
                    if not downloaded_size or elapsed_time <= 0:
                        download_speed = 0
                    else:
                        download_speed = downloaded_size / elapsed_time / 1024  # KB/s
                    progress = downloaded_size / total_size * 100
                    sys.stdout.write("\r[{:s}] Downloading... {:.2f}% ({:.2f} KB/s) total {:.2f} MB {:s}".format(
                        threading.current_thread().name,
                        progress,
                        download_speed,
                        total_mb,
                        file_name))
                    sys.stdout.flush()
                    if progress >= 100:
                        logger.info("\r[{:s}] finished {:.2f}% ({:.2f} KB/s) total {:.2f} MB saved: {:s}".format(
                            threading.current_thread().name,
                            progress,
                            download_speed,
                            total_mb,
                            save_path))

        except Exception as err:
            logger.error(f"download 出现异常, 准备重试 Error:{traceback.format_exc()}")
            raise err
        finally:
            thread_semaphore.release()


if __name__ == '__main__':
    # tests
    h = HttpClient()
    h.set_proxy('http://localhost:1087')
    # h.download('https://i.pximg.net/img-original/img/2024/06/17/18/24/53/119725660_p0.png', 'tmp.png')

    r = h.request(
        'https://www.pixiv.net/ajax/user/39805666/profile/top?lang=zh&version=f5f50bb540731f95e7b1eee0509ac311fd4e9525',
        "GET")
    print(r.json())
