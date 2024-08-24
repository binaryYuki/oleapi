import datetime
import hashlib
from _redis import get_key, set_key  # noqa
from fake_useragent import UserAgent

ua = UserAgent()


def he(char):
    # 将字符转换为二进制字符串，保持至少6位长度
    return bin(int(char))[2:].zfill(6)


def C(t):
    # 使用 hashlib 生成 MD5 哈希值
    return hashlib.md5(t.encode('utf-8')).hexdigest()


def vv_generator():
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


if __name__ == '__main__':
    print(vv_generator())
    print(_getRandomUserAgent())
