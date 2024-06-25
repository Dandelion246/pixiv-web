from typing import Any
from utils import config
try:
    # Python>=3.8
    from typing import Literal
except ImportError:
    # Python ==3.7
    from typing_extensions import Literal  # type: ignore[assignment]

try:
    # Python>=3.10
    from typing import TypeAlias  # type: ignore[attr-defined]
except ImportError:
    # Python==3.7, ==3.8, ==3.9
    from typing_extensions import TypeAlias

# 并发下载数
MAX_CONCURRENT_THREADS = int(config['Network']['max_concurrent_threads'])
# 重试次数
STOP_MAX_ATTEMPT_NUMBER = int(config['Network']['stop_max_attempt_number'])
# 重试间隔时间
WAIT_FIXED = int(config['Network']['wait_fixed'])

_TYPE: TypeAlias = Literal["illust", "manga", ""]
_CONTENT_TYPE: TypeAlias = Literal["illust", "manga", 'ugoira', ""]
_MODE: TypeAlias = Literal[
    "daily",  # 今日
    "weekly",  # 本周
    "monthly",  # 本月
    "rookie",  # 新人
    "original",  # 原创
    "daily_ai",  # AI生成
    "male",  # 受男性欢迎
    "female",  # 受女性欢迎
    "daily_r18",  # 今日r18
    "weekly_r18",  # 本周r18
    "daily_r18_ai",  # AI生成r18
    "male_r18",  # 受男性欢迎r18
    "female_r18",  # 受女性欢迎r18
    "r18g",
    "",
]

_SEARCH_URL_TYPE: TypeAlias = Literal[
    "artworks",
    "top",
    "illustrations",
    "manga",
    "novels",
]

_LANG = 'zh'
_HEADERS = {
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
    "Cookie": config['User']['cookies'],
    "X-User-Id": config['User']['user_id'],
}

_TYPE_DICT = {
    '0': 'illust',
    '1': 'manga',
    '2': 'ugoira',
}

_MENU_DICT = {
    '1': '获取所有关注的用户的所有作品',
    '2': '订阅关注的用户的最新作品',
    '3': '下载用户所有作品',
    '4': '下载收藏的所有作品',
    '5': '重试下载因各种异常而失败的作品',
}

class JsonDict(dict):  # type: ignore[type-arg]
    """general json object that allows attributes to be bound to and also behaves like a dict"""

    def __getattr__(self, attr: Any) -> Any:
        return self.get(attr)

    def __setattr__(self, attr: Any, value: Any) -> None:
        self[attr] = value
