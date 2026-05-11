from random import choice, randint, random
from re import compile
from time import time
from urllib.parse import urlencode, quote
from gmssl import sm3, func

__all__ = ["ABogus"]


class ABogus:
    __filter = compile(r'%([0-9A-F]{2})')
    __arguments = [0, 1, 14]
    __ua_key = "\u0000\u0001\u000e"
    __end_string = "cus"
    __browser = "1536|742|1536|864|0|0|0|0|1536|864|1536|864|1536|742|24|24|MacIntel"
    __reg = [
        1937774191, 1226093241, 388252375, 3666478592,
        2842636476, 372324522, 3817729613, 2969243214,
    ]
    __str = {
        "s0": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",
        "s1": "Dkdpgh4ZKsQB80/Mfvw36XI1R25+WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe=",
        "s2": "Dkdpgh4ZKsQB80/Mfvw36XI1R25-WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe=",
        "s3": "ckdp1h4ZKsUB80/Mfvw36XIgR25+WQAlEi7NLboqYTOPuzmFjJnryx9HVGDaStCe",
        "s4": "Dkdpgh2ZmsQB80/MfvV36XI1R45-WUAlEixNLwoqYTOPuzKFjJnry79HbGcaStCe",
    }

    def __init__(self):
        self.chunk: list[int] = []
        self.size = 0
        self.reg = self.__reg[:]
        self.ua_code = [
            76, 98, 15, 131, 97, 245, 224, 133, 122, 199, 241, 166, 79, 34,
            90, 191, 128, 126, 122, 98, 66, 11, 14, 40, 49, 110, 110, 173,
            67, 96, 138, 252,
        ]
        self.browser = self.__browser
        self.browser_len = len(self.browser)
        self.browser_code = self.char_code_at(self.browser)

    @classmethod
    def list_1(cls, random_num=None, a=170, b=85, c=45):
        return cls.random_list(random_num, a, b, 1, 2, 5, c & a)

    @classmethod
    def list_2(cls, random_num=None, a=170, b=85):
        return cls.random_list(random_num, a, b, 1, 0, 0, 0)

    @classmethod
    def list_3(cls, random_num=None, a=170, b=85):
        return cls.random_list(random_num, a, b, 1, 0, 5, 0)

    @staticmethod
    def random_list(a=None, b=170, c=85, d=0, e=0, f=0, g=0):
        r = a or (random() * 10000)
        v = [r, int(r) & 255, int(r) >> 8]
        s = v[1] & b | d
        v.append(s)
        s = v[1] & c | e
        v.append(s)
        s = v[2] & b | f
        v.append(s)
        s = v[2] & c | g
        v.append(s)
        return v[-4:]

    @staticmethod
    def from_char_code(*args):
        return "".join(chr(code) for code in args)

    @classmethod
    def generate_string_1(cls, r1=None, r2=None, r3=None):
        return (cls.from_char_code(*cls.list_1(r1)) +
                cls.from_char_code(*cls.list_2(r2)) +
                cls.from_char_code(*cls.list_3(r3)))

    def generate_string_2(self, url_params: str, method="GET", start_time=0, end_time=0):
        a = self.generate_string_2_list(url_params, method, start_time, end_time)
        e = self.end_check_num(a)
        a.extend(self.browser_code)
        a.append(e)
        return self.rc4_encrypt(self.from_char_code(*a), "y")

    def generate_string_2_list(self, url_params: str, method="GET", start_time=0, end_time=0):
        start_time = start_time or int(time() * 1000)
        end_time = end_time or (start_time + randint(4, 8))
        params_array = self.generate_params_code(url_params)
        method_array = self.generate_method_code(method)
        return self.list_4(
            (end_time >> 24) & 255,
            params_array[21],
            self.ua_code[23],
            (end_time >> 16) & 255,
            params_array[22],
            self.ua_code[24],
            (end_time >> 8) & 255,
            (end_time) & 255,
            (start_time >> 24) & 255,
            (start_time >> 16) & 255,
            (start_time >> 8) & 255,
            (start_time) & 255,
            method_array[21],
            method_array[22],
            int(end_time / 256 / 256 / 256 / 256) >> 0,
            int(start_time / 256 / 256 / 256 / 256) >> 0,
            self.browser_len,
        )

    @staticmethod
    def reg_to_array(a):
        o = [0] * 32
        for i in range(8):
            c = a[i]
            o[4 * i + 3] = 255 & c
            c >>= 8
            o[4 * i + 2] = 255 & c
            c >>= 8
            o[4 * i + 1] = 255 & c
            c >>= 8
            o[4 * i] = 255 & c
        return o

    @staticmethod
    def sm3_to_array(data: str | list) -> list[int]:
        if isinstance(data, str):
            b = data.encode("utf-8")
        else:
            b = bytes(data)
        h = sm3.sm3_hash(func.bytes_to_list(b))
        return [int(h[i: i + 2], 16) for i in range(0, len(h), 2)]

    @staticmethod
    def de(e, r):
        r %= 32
        return ((e << r) & 0xFFFFFFFF) | (e >> (32 - r))

    @staticmethod
    def pe(e):
        return 2043430169 if 0 <= e < 16 else 2055708042

    @staticmethod
    def he(e, r, t, n):
        if 0 <= e < 16:
            return (r ^ t ^ n) & 0xFFFFFFFF
        elif 16 <= e < 64:
            return (r & t | r & n | t & n) & 0xFFFFFFFF
        raise ValueError

    @staticmethod
    def ve(e, r, t, n):
        if 0 <= e < 16:
            return (r ^ t ^ n) & 0xFFFFFFFF
        elif 16 <= e < 64:
            return (r & t | ~r & n) & 0xFFFFFFFF
        raise ValueError

    @staticmethod
    def char_code_at(s):
        return [ord(char) for char in s]

    @staticmethod
    def generate_result(s, e="s4"):
        r = []
        for i in range(0, len(s), 3):
            if i + 2 < len(s):
                n = (ord(s[i]) << 16) | (ord(s[i + 1]) << 8) | ord(s[i + 2])
            elif i + 1 < len(s):
                n = (ord(s[i]) << 16) | (ord(s[i + 1]) << 8)
            else:
                n = ord(s[i]) << 16
            for j, k in zip(range(18, -1, -6), (0xFC0000, 0x03F000, 0x0FC0, 0x3F)):
                if j == 6 and i + 1 >= len(s):
                    break
                if j == 0 and i + 2 >= len(s):
                    break
                r.append(ABogus.__str[e][(n & k) >> j])
        r.append("=" * ((4 - len(r) % 4) % 4))
        return "".join(r)

    @staticmethod
    def compress_block(reg, chunk):
        i = reg[:]
        f = [0] * 132
        for t in range(16):
            f[t] = (chunk[4 * t] << 24) | (chunk[4 * t + 1] << 16) | \
                   (chunk[4 * t + 2] << 8) | chunk[4 * t + 3]
            f[t] &= 0xFFFFFFFF
        for n in range(16, 68):
            a = f[n - 16] ^ f[n - 9] ^ ABogus.de(f[n - 3], 15)
            a = a ^ ABogus.de(a, 15) ^ ABogus.de(a, 23)
            f[n] = (a ^ ABogus.de(f[n - 13], 7) ^ f[n - 6]) & 0xFFFFFFFF
        for n in range(68, 132):
            f[n] = (f[n - 68] ^ f[n - 64]) & 0xFFFFFFFF
        for o in range(64):
            c = ABogus.de(i[0], 12) + i[4] + ABogus.de(ABogus.pe(o), o)
            c = (c & 0xFFFFFFFF)
            c = ABogus.de(c, 7)
            s = (c ^ ABogus.de(i[0], 12)) & 0xFFFFFFFF
            u = ABogus.he(o, i[0], i[1], i[2])
            u = (u + i[3] + s + f[o + 68]) & 0xFFFFFFFF
            b = ABogus.ve(o, i[4], i[5], i[6])
            b = (b + i[7] + c + f[o]) & 0xFFFFFFFF
            i[3] = i[2]
            i[2] = ABogus.de(i[1], 9)
            i[1] = i[0]
            i[0] = u
            i[7] = i[6]
            i[6] = ABogus.de(i[5], 19)
            i[5] = i[4]
            i[4] = (b ^ ABogus.de(b, 9) ^ ABogus.de(b, 17)) & 0xFFFFFFFF
        for l in range(8):
            reg[l] = (reg[l] ^ i[l]) & 0xFFFFFFFF

    @classmethod
    def pad_array(cls, arr, length=60):
        while len(arr) < length:
            arr.append(0)
        return arr

    def fill(self, length=60):
        size = 8 * self.size
        self.chunk.append(128)
        self.chunk = self.pad_array(self.chunk, length)
        for i in range(4):
            self.chunk.append((size >> 8 * (3 - i)) & 255)

    @staticmethod
    def split_array(arr, chunk_size=64):
        result = []
        for i in range(0, len(arr), chunk_size):
            result.append(arr[i:i + chunk_size])
        return result

    def write(self, e):
        self.size = len(e)
        if isinstance(e, str):
            e = self.decode_string(e)
            e = self.char_code_at(e)
        if len(e) <= 64:
            self.chunk = e
        else:
            chunks = self.split_array(e, 64)
            for ch in chunks[:-1]:
                self.compress_block(self.reg, ch)
            self.chunk = chunks[-1]

    def reset(self):
        self.chunk = []
        self.size = 0
        self.reg = self.__reg[:]

    def sum(self, e, length=60):
        self.reset()
        self.write(e)
        self.fill(length)
        self.compress_block(self.reg, self.chunk)
        return self.reg_to_array(self.reg)

    @classmethod
    def decode_string(cls, url_string):
        return cls.__filter.sub(cls.replace_func, url_string)

    @staticmethod
    def replace_func(match):
        return chr(int(match.group(1), 16))

    @staticmethod
    def generate_args_code():
        a = []
        for j in range(24, -1, -8):
            a.append(ABogus.__arguments[0] >> j)
        a.append(ABogus.__arguments[1] / 256)
        a.append(ABogus.__arguments[1] % 256)
        a.append(ABogus.__arguments[1] >> 24)
        a.append(ABogus.__arguments[1] >> 16)
        for j in range(24, -1, -8):
            a.append(ABogus.__arguments[2] >> j)
        return [int(i) & 255 for i in a]

    def generate_method_code(self, method: str = "GET") -> list[int]:
        return self.sum(method + self.__end_string)

    def generate_params_code(self, params: str) -> list[int]:
        return self.sum(params + self.__end_string)

    @staticmethod
    def end_check_num(a: list):
        r = 0
        for i in a:
            r ^= i
        return r

    @staticmethod
    def list_4(a, b, c, d, e, f, g, h, i, j, k, m, n, o, p, q, r):
        return [
            44, a, 0, 0, 0, 0, 24, b, n, 0, c, d, 0, 0, 0, 1, 0, 239,
            e, o, f, g, 0, 0, 0, 0, h, 0, 0, 14, i, j, 0, k, m, 3, p, 1,
            q, 1, r, 0, 0, 0,
        ]

    @staticmethod
    def rc4_encrypt(plaintext, key):
        s = list(range(256))
        j = 0
        for i in range(256):
            j = (j + s[i] + ord(key[i % len(key)])) % 256
            s[i], s[j] = s[j], s[i]
        i = j = 0
        cipher = []
        for k in range(len(plaintext)):
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            t = (s[i] + s[j]) % 256
            cipher.append(chr(s[t] ^ ord(plaintext[k])))
        return ''.join(cipher)

    def get_value(self, url_params: dict | str, method="GET",
                  start_time=0, end_time=0, r1=None, r2=None, r3=None) -> str:
        string_1 = self.generate_string_1(r1, r2, r3)
        string_2 = self.generate_string_2(
            urlencode(url_params) if isinstance(url_params, dict) else url_params,
            method, start_time, end_time,
        )
        string = string_1 + string_2
        return self.generate_result(string, "s4")
