from scheduler.strategies.seoul import SeoulStrategy
from scheduler.strategies.singapore import SingaporeStrategy
from scheduler.strategies.hongkong import HongKongStrategy
from scheduler.strategies.base import CityStrategy

STRATEGY_REGISTRY: dict[str, CityStrategy] = {
    "SEOUL":      SeoulStrategy(),
    "SINGAPORE":  SingaporeStrategy(),
    "HONG_KONG":  HongKongStrategy(),
    # เพิ่มเมืองใหม่ตรงนี้
    # "TOKYO":    TokyoStrategy(),
    # "SHANGHAI": ShanghaiStrategy(),
}