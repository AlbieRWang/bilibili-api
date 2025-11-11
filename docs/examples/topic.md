# 示例：获取话题下的内容

``` python
from bilibili_api import topic, sync

t = topic.Topic(topic_id=66573)
print(sync(t.get_cards(10)))
```


# 示例：遍历话题下的所有动态

``` python
from bilibili_api import topic, sync

# limit 控制最多返回多少条动态，save_item=True 会缓存原始数据
t = topic.Topic(topic_id=66573)
dynamics = sync(t.get_dynamics(limit=5))
print([d.get_dynamic_id() for d in dynamics])
print(t.get_saved_dynamic_item(dynamics[0].get_dynamic_id()))
```
