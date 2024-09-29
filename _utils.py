import datetime
import hashlib
import json
import logging
import uuid

from fake_useragent import UserAgent
from httpx import AsyncClient

from _redis import get_key, set_key  # noqa

ua = UserAgent()

logger = logging.getLogger(__name__)


def he(char):
    # 将字符转换为二进制字符串，保持至少6位长度
    return bin(int(char))[2:].zfill(6)


def C(t):
    # 使用 hashlib 生成 MD5 哈希值
    return hashlib.md5(t.encode('utf-8')).hexdigest()


def vv_generator():
    """
    生成 vv 参数
    :return:
    """
    # 获取当前法国时间的 Unix 时间戳（秒）
    france_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2)))
    timestamp = int(france_time.timestamp())

    # 将时间戳转换为字符串
    t = str(timestamp)

    r = ["", "", "", ""]

    # 遍历时间戳字符串并处理二进制表示
    for char in t:
        e = he(char)
        r[0] += e[2] if len(e) > 2 else '0'
        r[1] += e[3] if len(e) > 3 else '0'
        r[2] += e[4] if len(e) > 4 else '0'
        r[3] += e[5] if len(e) > 5 else '0'

    a = []

    # 将二进制字符串转换为十六进制字符串
    for binary_str in r:
        hex_str = format(int(binary_str, 2), 'x').zfill(3)
        a.append(hex_str)

    n = C(t)

    # 组合最终结果字符串
    vv = n[:3] + a[0] + n[6:11] + a[1] + n[14:19] + a[2] + n[22:27] + a[3] + n[30:]

    return vv


async def generate_vv_detail():
    """
    生成 vv 参数
    :return:  str
    """
    vv = await get_key('vv')

    if not vv:
        vv = vv_generator()
        success = await set_key('vv', vv, 60 * 5)
        if not success:
            raise Exception('Failed to set vv')

    return vv


def _getRandomUserAgent():
    return ua.random


async def pushNotification(baseURL: str, msg: str, icon: str = '', click_url: str = '', is_passive: bool = False,
                           headers=None):
    """
    推送通知
    :param baseURL: str
    :param msg: str
    :param icon: str
    :param click_url: str
    :param is_passive: bool
    :param headers: dict
    :param data: dict
    :param log_data: dict -> {'push_id': str, 'push_receiver': str}
    """
    # url = https://api.day.app/uKeSrwm3ainGgn5SAmRyg9/{msg}?icon={icon}&url={url}&passive={is_passive}
    if headers is None:
        headers = {}
    print(f"Pushing notification to {baseURL}/{msg}?")
    url = f'{baseURL}/{msg}?'
    if icon:
        url += f'&icon={icon}'
    if click_url:
        url += f'&url={click_url}'
    if is_passive:
        url += f'&passive=true'
    print(f"Pushing to {url}")
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers)
        print(response.status_code)
        if response.status_code != 200:
            return False
        else:
            return True


async def generatePushTask(baseURL: str, msg: str, user_id: str, receiver: str, icon=None, click_url=None,
                           is_passive=None, headers: dict = None, taskID: str = uuid.uuid4().hex,
                           push_receiver: str = "yuki", push_by: str = "system"):
    """
    :param push_by:  推送者 默认为system
    :param push_channel:  推送渠道 默认为bark
    :param push_receiver: 用户email
    :param taskID:  任务ID 默认为uuid
    :param headers:  请求头
    :param icon:  图标
    :param user_id:  用户ID
    :param msg:  消息
    :param baseURL:  基础URL
    :param click_url: 点击通知后跳转的URL
    :param receiver: 接收者
    :param is_passive: 是否被动推送 就是不会有声音
    示例： generatePushTask("https://api.day.app/uKeSrwm3ainGgn5SAmRyg9/", "You have a new notification!", str(12345),
                           "https://example.com", False, None, None, None, uuid.uuid4().hex, "system",
                            "bark")
    """
    data = {
        "baseURL": baseURL,
        "msg": msg,
        "push_receiver": receiver,
        "icon": icon if icon else "https://static.olelive.com/snap/fa77502e442ee6bbd39be20b2a2810ee.jpg?_n=202409290554",
        "click_url": click_url if click_url else "",
        "is_passive": is_passive if is_passive is not None else False,
        "headers": headers if headers else {
            "content-type": "application/json",
        },
        "log_data": {
            "push_id": taskID,
            "push_receiver": push_receiver,
            "push_by": push_by if push_by else "system",
            "user_id": user_id
        }
    }
    await set_key(f"pushTask:{taskID}", json.dumps(data), 60 * 5)
    return True


if __name__ == '__main__':
    print(vv_generator())
    print(_getRandomUserAgent())
