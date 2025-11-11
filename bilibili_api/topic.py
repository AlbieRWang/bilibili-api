"""
bilibili_api.topic

话题相关
"""

from enum import Enum
from typing import Dict, List, Optional, Union

from . import dynamic
from .exceptions import ArgsException
from .user import get_self_info
from .utils.utils import get_api
from .utils.network import Api, Credential

API = get_api("topic")


class TopicCardsSortBy(Enum):
    """
    话题下内容排序方式

    + NEW: 最新
    + HOT: 最热
    + RECOMMEND: 推荐
    """

    NEW = 3
    HOT = 2
    RECOMMEND = 1


async def get_hot_topics(numbers: int = 33) -> dict:
    """
    获取动态页的火热话题

    Args:
        numbers (int): 话题数量. Defaults to 33.

    Returns:
        dict: 调用 API 返回的结果
    """
    api = API["info"]["dynamic_page_topics"]
    params = {"page_size": numbers}
    return await Api(**api).update_params(**params).result


async def search_topic(keyword: str, ps: int = 20, pn: int = 1) -> dict:
    """
    搜索话题

    从动态页发布动态处的话题搜索框搜索话题

    Args:
        keyword (str): 搜索关键词

        ps      (int): 每页数量. Defaults to 20.

        pn      (int): 页数. Defaults to 1.

    Returns:
        dict: 调用 API 返回的结果
    """
    api = API["info"]["search"]
    params = {"keywords": keyword, "page_size": ps, "page_num": pn}
    return await Api(**api).update_params(**params).result


class Topic:
    """
    话题类

    Attributes:
        credential (Credential): 凭据类
    """

    def __init__(self, topic_id: int, credential: Union[Credential, None] = None):
        """
        Args:
            topic_id   (int)       : 话题 id

            credential (Credential): 凭据类
        """
        self.__topic_id = topic_id
        self.credential: Credential = credential if credential else Credential()
        self.__info_cache: Optional[dict] = None
        self.__dynamic_item_cache: Dict[int, dict] = {}

    def get_topic_id(self) -> int:
        """
        获取话题 id

        Returns:
            int: 话题 id
        """
        return self.__topic_id

    async def get_info(self, refresh: bool = False) -> dict:
        """
        获取话题简介

        Args:
            refresh (bool): 是否强制刷新缓存. Defaults to False.

        Returns:
            dict: 调用 API 返回的结果
        """
        if refresh or self.__info_cache is None:
            api = API["info"]["info"]
            params = {"topic_id": self.get_topic_id()}
            self.__info_cache = (
                await Api(**api, credential=self.credential).update_params(**params).result
            )
        return self.__info_cache

    async def get_cards(
        self,
        ps: int = 100,
        offset: Optional[str] = None,
        sort_by: TopicCardsSortBy = TopicCardsSortBy.HOT,
    ) -> dict:
        """
        获取话题下的内容

        未登录无法使用热门排序字段即 TopicCardsSortBy.RECOMMEND

        Args:
            ps (int): 数据数量. Defaults to 100.

            offset (Optional, str): 偏移量. 生成格式为 f'{页码}_{页码*数据量]}' 如'2_40' Defaults to None.

            sort_by (TopicCardsSortBy): 排序方式. Defaults to TopicCardsSortBy.HOT.

        Returns:
            dict: 调用 API 返回的结果
        """
        api = API["info"]["cards"]
        params = {
            "topic_id": self.get_topic_id(),
            "page_size": ps,
            "sort_by": sort_by.value,
            "source": "Web",
        }
        if offset:
            params.update({"offset": offset})
        return (
            await Api(**api, credential=self.credential).update_params(**params).result
        )

    async def get_dynamics(
        self,
        ps: int = 100,
        sort_by: TopicCardsSortBy = TopicCardsSortBy.HOT,
        limit: Optional[int] = None,
        save_item: bool = True,
    ) -> List[dynamic.Dynamic]:
        """
        获取话题下的所有动态。

        会自动根据分页信息持续请求直到没有更多数据或达到 limit。

        Args:
            ps (int): 每次请求的数据数量. Defaults to 100.

            sort_by (TopicCardsSortBy): 排序方式. Defaults to TopicCardsSortBy.HOT.

            limit (Optional[int]): 限制返回的动态数量，None 为全部. Defaults to None.

            save_item (bool): 是否保存动态的原始数据以供后续使用. Defaults to True.

        Returns:
            List[dynamic.Dynamic]: 动态对象列表
        """
        if ps <= 0:
            raise ArgsException("ps 必须大于 0")
        if limit is not None and limit <= 0:
            return []
        dynamics: List[dynamic.Dynamic] = []
        remaining = limit
        seen_ids: set[int] = set()
        offset: Optional[str] = None
        visited_offsets: set[str] = set()

        while True:
            page_size = ps if remaining is None else min(ps, remaining)
            if page_size <= 0:
                break
            response = await self.get_cards(ps=page_size, offset=offset, sort_by=sort_by)
            card_list = response.get("topic_card_list") or {}
            items = card_list.get("items") or []
            if not items:
                break
            for item in items:
                card = item.get("dynamic_card_item")
                if not isinstance(card, dict):
                    continue
                dynamic_id_str = card.get("id_str")
                if not dynamic_id_str:
                    continue
                try:
                    dynamic_id = int(dynamic_id_str)
                except (TypeError, ValueError):
                    continue
                if dynamic_id in seen_ids:
                    continue
                if save_item:
                    self.__dynamic_item_cache[dynamic_id] = item
                dynamics.append(dynamic.Dynamic(dynamic_id, credential=self.credential))
                seen_ids.add(dynamic_id)
                if remaining is not None:
                    remaining -= 1
                    if remaining <= 0:
                        return dynamics
            if not card_list.get("has_more"):
                break
            next_offset = card_list.get("offset")
            if not next_offset or next_offset in visited_offsets:
                break
            visited_offsets.add(next_offset)
            offset = next_offset
        return dynamics

    def get_saved_dynamic_items(self) -> Dict[int, dict]:
        """
        获取已保存的动态原始数据。

        Returns:
            Dict[int, dict]: 动态 ID 与对应原始数据的映射
        """
        return self.__dynamic_item_cache.copy()

    def get_saved_dynamic_item(self, dynamic_id: int) -> Optional[dict]:
        """
        获取指定动态的已保存原始数据。

        Args:
            dynamic_id (int): 动态 ID

        Returns:
            Optional[dict]: 原始数据，若未保存则为 None
        """
        return self.__dynamic_item_cache.get(dynamic_id)

    def clear_saved_dynamic_items(self) -> None:
        """
        清空已保存的动态原始数据。
        """
        self.__dynamic_item_cache.clear()

    async def like(self, status: bool = True) -> dict:
        """
        设置点赞话题

        Args:
            status (bool): 是否设置点赞. Defaults to True.

        Returns:
            dict: 调用 API 返回的结果
        """
        api = API["operate"]["like"]
        data = {
            "topic_id": self.get_topic_id(),
            "action": "like" if status else "cancel_like",
            "business": "topic",
            "up_mid": (await get_self_info(self.credential))["mid"],
        }
        return await Api(**api, credential=self.credential).update_data(**data).result

    async def set_favorite(self, status: bool = True) -> dict:
        """
        设置收藏话题

        Args:
            status (bool): 是否设置收藏. Defaults to True.

        Returns:
            dict: 调用 API 返回的结果
        """
        api = API["operate"]["add_favorite" if status else "cancel_favorite"]
        data = {"topic_id": self.get_topic_id()}
        return await Api(**api, credential=self.credential).update_data(**data).result
