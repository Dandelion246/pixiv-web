from typing import Any
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


TYPE: TypeAlias = Literal["illust", "manga", ""]
CONTENT_TYPE: TypeAlias = Literal["illust", "manga", 'ugoira', ""]
MODE: TypeAlias = Literal[
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

SEARCH_URL_TYPE: TypeAlias = Literal[
    "artworks",
    "top",
    "illustrations",
    "manga",
    "novels",
]

LANG = 'zh'

TYPE_DICT = {
    '0': 'illust',
    '1': 'manga',
    '2': 'ugoira',
}

MENU_DICT = {
    '0': '抓取单个作品',
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
