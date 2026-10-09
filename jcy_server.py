# -*- coding: utf-8 -*-
"""本地后端: 电脑版 UI 只留界面, 数据/播放由本服务提供.

- /pc/* 转发真实 PC 后端, 返回明文 JSON
- /pc/video/play 优先真实 PC source, 再查 app 收集的 source 映射, 最后 vo1v03 转直链
- /api/resolve 直接用 vo1v03 签名解析 source
"""
import base64
import hashlib
import http.server
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

import requests
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad

requests.packages.urllib3.disable_warnings()

HOST, PORT = "43.145.33.254", 27990
APPID = "4150439554430529"
VERSION = "2024-07-02"
PLANFORM, INTERNAL, APP_VERSION, SYMBOL = "3", "1.0.0", "1.1.5", "win32"
AES_KEY = b"ziISjqkXPsGUMRNGyWigxDGtJbfTdcGv"
AES_IV = b"WonrnVkxeIxDcFbv"
TOKEN = ""
PARAMS_KEY = b"R5xThLNmXbpDOgyj"
SECRET = "ktbzycpyap"
VO_VERSION = "1.5.8.0"
VO = "http://yh.jx.xajtl.com/vo1v03.php"
VO_AES_KEY = b"vqrzbkuzashmnqpr"
VO_AES_IV = b"dflprvkvvixnvsjx"
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE_DIR, "source_cache.json")
SOURCE_MAP = os.path.join(BASE_DIR, "source_map.json")
URL_CACHE = os.path.join(BASE_DIR, "playurl_cache.json")
SEND_B64 = "LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlJQklqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FROEFNSUlCQ2dLQ0FRRUFyMTBEYjM5YXBoWDlnWm5seDRyLwpZMU5rbEV4RVBQbk0xM2gvR3c2RHg0b1hlVmFFOW43NmZEQ0tYZ01SZzRkZjRaRGVYNzZibCtBRjdDdkhCQVRGCmFLcGk0eDhtZTBXMk5sOFpvdmxYbVl5N1hDa3FoRENNK29JcTlGMldhTUE1UzBqTmVKOW9QbUd4bXo0MUlTUkYKbTNqRGxuVS91U3pVTnJneGZmbWNMemVOTDBOYThkZkJVaU5NZXZkdlRkMnlwYWh0a21yS0lpNEdRNlFvSGVpdwpmUzZaWTA1eC8vTUphVzhzN0N5VHA1eUUvbDlISXBuc3FCcUx3azJ5NjJwSGJEZHRUWEIrSEhNVHE5Uzk3dVhICkpuYmZRMWRWdndmYzZUTGtub1Jmam44bzZTUnRLdVZVNW81eDZMekZFTStTOXFaTS9MdmMwaHJsNWFXRnJmaFEKMndJREFRQUIKLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg=="


RECV_PEM = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0fciNSCS8o6Y7pJVH+4SxVgDJCipDou4teBUlfStdaKAh08g
y5V2izx/XdzeGf9g4Xgd7UwxPr+QKG/RvFAfAO0AYQK4uPOnjzDQvGPUBEKwRoGv
cM8zo4wvfbLUjfXywpDDLrT/PdolliWn3gJ83nl86Oe2pOiNlG1ojxP8IXjUWrYB
275EyyulYxG2nWK8RLJG2OcXNdqttM4ILFgIbawB8l94nlRSxb1g2fa5PKGxq33L
gTt0GnGoVduXfpCUM19q0ju8WSDdXjEUhnRWWBWiRu4Pum24pI5qrJiiANvkg6fe
k/tE0THUBlU0N5CG6UwVvoDs/opBiMmUg001eQIDAQABAoIBADN7Ofr2yrEIf7z3
SkHy+M1EYDjMc28qmRaXM4Y1IRbXylXi8/KW6iMHqV8VWavcLx/5eLUHWoe9JpaT
nERlDMUIV3Bx32MR8wKsAHJAs+p7g4c2IxMw6sNuCvLyFyXbqTNFlWXtYSwEQfUH
tJo91+ogtZzRu7nBf31mOh3i045NBWnOAydv4QEhJerqQYh2byJwbgwjROPGT7oL
5kGFQVtNHrQcXVV1dfrTD3raksRelGCxqh3gJWGj7JyTcM8bhOaQXcRGg2wbJ17f
AYxFX9ZHzPekWzYYwhr97Pd/QAC6IYgw9/y85IX03Zub22vj33FlMX/WIWsf5ebo
+z7/OgECgYEA5bviZ9Gy7Rj4Su9QXmDNLrPK+WXgQ3L8WqsEZG+YIFy80M3Y2Ax+
Md7l0qeXTcA6IRKniO+hA6Pf7sTVEr+AGHLd3cCP311XDiDLENP4TTOtoKjSfsq5
dzzYCSMlXPkVuAt6hHcn5eMpzD7W6grqmq1ZM05NbvOTXKoEuqbZg8ECgYEA6fij
861vZmaKWneTdJU5+GtUGwSJwAmduxyXsK7JIfexCz0LBm/sBu3d+I4zKzQ/BhHu
GKUZWAs8N7PZtq6mYX7xzDXg83wO1Q3qz6Eazid0dezJhbanlj5GThP8QUFIsddT
qfcFygnPMchUjJyoCU30+SPRBFbvjJ0mWRrQv7kCgYEAnTwt5m7A7sQTVH5c3GuW
o2tM9ctDZgayL4AzPmaekS/Hz4XD74MFcC6lz7sCtKVnY7F31yJjarFjl/FCAFXv
X0xnC9o63l7tMW9CbN8XaAeBw58oir1HmROcrQxQC0U0F0ZL8ZP4S8BhoDg2MfOM
xJb2oUXre4/cgSSgnfuKjkECgYA6y52/vYSyEfCQnV3zvRBNSgNfqrtHA+OcQqon
3zRyEcFu1o8vte51K09Nh8Z6A+4Wg2j2zn5Y7rHaOZrrWmY7N+BhdeSqqzE6/v1T
4eNPjQCqJa/apzTj/5BBTKpmZ5ZyAm9m1cmhpOdpVjNRBoj/lZSLCyIaWhJmnpMl
bySoGQKBgQCmDZ0nnO4tu4AVkCexeAhlTvU6WC6kx5hHbP1SvY/2qmR9lounFUCi
rxguVdl8wpXekTLxNTBr2VrOpxEIaorXj6VhiG1YVn70H+0lVmJMp9GadEzaAq1v
ee1htE2bN5WH4J9wX3n+dyroM0UWiD5J5NxgypT7PRxIk4rznBOnCQ==
-----END RSA PRIVATE KEY-----"""


RECV = RECV_PEM


def aes_cbc(key, iv, data, enc=True):
    c = AES.new(key, AES.MODE_CBC, iv)
    if enc:
        return c.encrypt(pad(data if isinstance(data, bytes) else data.encode(), 16))
    return c.decrypt(data)


def auth_str():
    return "%s-%d-%s-%s-%s" % (APP_VERSION, int(time.time() * 1000), PLANFORM, INTERNAL, SYMBOL)


def auth_header():
    v = base64.b64encode(auth_str().encode())
    return base64.b64encode(aes_cbc(AES_KEY, AES_IV, v)).decode()


def params_decrypt(text):
    if not isinstance(text, str) or "." not in text:
        return text
    rsa_part, ct = text.split(".", 1)
    try:
        rsa_raw = base64.b64decode(rsa_part, validate=False)
    except Exception:
        return text
    try:
        key = RSA.import_key(RECV)
        _key = PKCS1_v1_5.new(key).decrypt(rsa_raw, None)
    except Exception:
        return text
    if not _key:
        return text
    _key = _key.decode()
    _iv = _key[::-1].encode()
    raw = aes_cbc(_key.encode(), _iv, base64.b64decode(ct), enc=False)
    try:
        return unpad(raw, 16).decode("utf-8", "ignore")
    except Exception:
        return text


def params_encrypt(obj):
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    rsa = PKCS1_v1_5.new(RSA.import_key(base64.b64decode(SEND_B64).decode()))
    rsa_part = base64.b64encode(rsa.encrypt(PARAMS_KEY)).decode()
    iv = PARAMS_KEY[::-1]
    ct = base64.b64encode(aes_cbc(PARAMS_KEY, iv, text.encode())).decode()
    return rsa_part + "." + ct


def upstream_post(path, obj, timeout=25, x_token=None):
    headers = {
        "Content-Type": "application/json",
        "ts": str(int(time.time() * 1000)),
        "X-VERSION": VERSION,
        "APPID": APPID,
        "Authentication": auth_header(),
        "system": "3",
        "X-Token": x_token or TOKEN,
        "user-agent": "Dart/3.6 (dart:io)",
    }
    body = params_encrypt(obj)
    url = "http://%s:%s%s" % (HOST, PORT, path)
    r = requests.post(url, data=body, headers=headers, timeout=timeout, verify=False)
    if r.status_code != 200:
        return {"code": r.status_code, "message": "upstream http %d" % r.status_code}
    txt = params_decrypt(r.text)
    try:
        return json.loads(txt)
    except Exception:
        return {"code": 50000, "message": txt[:200]}


def upstream_post_raw(path, body, content_type, timeout=25, x_token=None):
    headers = {
        "Content-Type": content_type,
        "ts": str(int(time.time() * 1000)),
        "X-VERSION": VERSION,
        "APPID": APPID,
        "Authentication": auth_header(),
        "system": "3",
        "X-Token": x_token or TOKEN,
        "user-agent": "Dart/3.6 (dart:io)",
    }
    url = "http://%s:%s%s" % (HOST, PORT, path)
    r = requests.post(url, data=body, headers=headers, timeout=timeout, verify=False)
    if r.status_code != 200:
        return {"code": r.status_code, "message": "upstream http %d" % r.status_code}
    txt = params_decrypt(r.text)
    try:
        return json.loads(txt)
    except Exception:
        return {"code": 50000, "message": txt[:200]}


def upstream_get(path, timeout=25, x_token=None):
    headers = {
        "Content-Type": "application/json",
        "ts": str(int(time.time() * 1000)),
        "X-VERSION": VERSION,
        "APPID": APPID,
        "Authentication": auth_header(),
        "system": "3",
        "X-Token": x_token or TOKEN,
        "user-agent": "Dart/3.6 (dart:io)",
    }
    url = "http://%s:%s%s" % (HOST, PORT, path)
    r = requests.get(url, headers=headers, timeout=timeout, verify=False)
    if r.status_code != 200:
        return {"code": r.status_code, "message": "upstream http %d" % r.status_code}
    txt = params_decrypt(r.text)
    try:
        return json.loads(txt)
    except Exception:
        return {"code": 50000, "message": txt[:200]}


def _vo_aes_dec(b64, aes_key=None, aes_iv=None):
    if aes_key is None:
        aes_key = VO_AES_KEY
    if aes_iv is None:
        aes_iv = VO_AES_IV
    raw = base64.b64decode(b64)
    c = AES.new(aes_key, AES.MODE_CBC, aes_iv)
    return unpad(c.decrypt(raw), 16).decode("utf-8", "ignore")


def _vo_config_from_parse(parse_text=None):
    """从 play 返回的 Lua parse 字段提取当前 VO 密钥/盐, 服务器换参后不写死."""
    cfg = {
        "version": VO_VERSION,
        "secret": SECRET,
        "aes_key": VO_AES_KEY.decode(),
        "aes_iv": VO_AES_IV.decode(),
        "platform": "Android",
    }
    if not parse_text:
        return cfg
    m = re.search(r'aes_key\s*=\s*"([^"]+)"', parse_text)
    if m:
        cfg["aes_key"] = m.group(1)
    m = re.search(r'aes_iv\s*=\s*"([^"]+)"', parse_text)
    if m:
        cfg["aes_iv"] = m.group(1)
    m = re.search(r'utils\.md5\(data \.\. "([^"]+)" \.\. ts\)', parse_text)
    if not m:
        m = re.search(r'data \.\. "([^"]+)" \.\. ts', parse_text)
    if m:
        cfg["secret"] = m.group(1)
    return cfg


def md5sign(text):
    return hashlib.md5(text.encode()).hexdigest()


def resolve_source(source, retries=2, config=None):
    cfg = config or _vo_config_from_parse()
    last_err = None
    for _ in range(retries + 1):
        try:
            ts = str(int(time.time()))
            url = VO + "?url=" + urllib.parse.quote(source, safe="|") + "&t=" + ts
            headers = {
                "x-time": ts,
                "x-form": "Android",
                "x-sign1": md5sign(cfg["version"] + cfg["secret"] + ts),
                "x-sign2": md5sign(source + cfg["secret"] + ts),
                "user-agent": "Dart/3.6 (dart:io)",
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read()
            try:
                obj = json.loads(raw.decode("utf-8", "replace"))
            except Exception:
                obj = json.loads(_vo_aes_dec(raw, cfg["aes_key"].encode(), cfg["aes_iv"].encode()))
            addrs = obj.get("data", {}).get("playAddr", [])
            if not addrs and obj.get("url"):
                return [{
                    "title": None,
                    "desc": obj.get("type") or "高清",
                    "vcodec": None,
                    "url": obj.get("url"),
                }]
            return [{
                "title": it.get("title"),
                "desc": it.get("desc"),
                "vcodec": it.get("vcodec"),
                "url": (it.get("m3u8FileDomain") or "") + (it.get("addr") or ""),
            } for it in addrs]
        except Exception as e:
            last_err = str(e)
            time.sleep(1)
    raise RuntimeError("resolve failed: %s" % last_err)


def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def find_source(vid, part):
    m = load_json(SOURCE_MAP) or {}
    key = "%s|%s" % (vid, part)
    if key in m:
        return m[key]
    for k, v in (m or {}).items():
        if k.startswith(str(vid) + "|") and v:
            return v
    return None


def play_payload(vid, part, x_token=None):
    """先真实 PC 链路, 再本地 source, 最后 vo1v03/url 缓存."""
    # 1) 真实 PC play
    try:
        path = "/pc/video/play?id=%s&play=mp4&part=%s" % (vid, urllib.parse.quote(part))
        o = upstream_get(path, timeout=20, x_token=x_token)
        if o.get("code") == 20000:
            data = o.get("data") or []
            if data and data[0].get("url"):
                vo_cfg = _vo_config_from_parse(data[0].get("parse") or "")
                addrs = resolve_source(data[0]["url"], config=vo_cfg)
                if addrs:
                    return _payload(addrs)
    except Exception:
        pass
    # 2) 本地 source 映射, 只返回该 vid+part 的 source
    source = find_source(vid, part)
    if isinstance(source, str) and source:
        try:
            addrs = resolve_source(source)
            if addrs:
                return _payload(addrs)
        except Exception:
            pass
    return []


def _payload(addrs):
    out = []
    for a in addrs:
        out.append({
            "resolution": a.get("desc") or a.get("title") or "高清",
            "url": a.get("url") or "",
            "play": "url",
            "ps": 0,
            "vip_type": 0,
            "completeness": 100,
            "total_duration": 0,
            "type": "auto",
            "lua_header": {},
            "extension": {"url": "auto"},
        })
    return out


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(self.command, self.path, flush=True)

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        x_token = self.headers.get("X-Token")

        if path == "/api/health":
            return self._json({"code": 20000, "message": "ok", "status": "alive"})

        if path == "/api/resolve":
            src = qs.get("source", [""])[0]
            try:
                return self._json({"code": 200, "source": src, "data": resolve_source(src)})
            except Exception as e:
                return self._json({"code": 500, "message": str(e)}, 500)

        if path == "/api/sources":
            return self._json({"code": 200, "data": load_json(CACHE) or []})

        if path == "/api/play":
            return self._json({"code": 200, "data": play_payload(qs.get("id", ["0"])[0], qs.get("part", [""])[0], x_token)})

        if path == "/pc/video/play":
            vid = qs.get("id", ["0"])[0]
            part = qs.get("part", [""])[0]
            data = play_payload(vid, part, x_token)
            if not data:
                return self._json({"code": 403101, "message": "暂无可用播放源，请在模拟器播放该集后重试", "data": []})
            return self._json({"code": 20000, "message": "ok", "data": data})

        # 其他 /pc/* 全部转发真实后端
        if path.startswith("/pc/") or path.startswith("/app/"):
            full = path
            if parsed.query:
                full += "?" + parsed.query
            return self._json(upstream_get(full, x_token=x_token))

        return self._json({"code": 20000, "message": "ok", "data": {}})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        path = urllib.parse.urlparse(self.path).path
        parsed = urllib.parse.urlparse(self.path)
        full = path + ("?" + parsed.query if parsed.query else "")
        x_token = self.headers.get("X-Token")
        if path.startswith("/pc/") or path.startswith("/app/"):
            ct = self.headers.get("Content-Type") or ""
            if "multipart/form-data" in ct:
                return self._json(upstream_post_raw(full, body, ct, x_token=x_token))
            try:
                obj = json.loads(body.decode("utf-8", "replace")) if body else {}
            except Exception:
                obj = body.decode("utf-8", "replace")
            return self._json(upstream_post(full, obj, x_token=x_token))
        return self._json({"code": 20000, "message": "ok", "data": {}})


def port_in_use(port):
    import socket
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=0.5)
        s.close()
        return True
    except Exception:
        return False





EXPIRED_CODES = {50014, 500403}  # 50008不是token过期，不fallback


def _fallback(fn):
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        if not isinstance(result, dict):
            return result
        if result.get("code") not in EXPIRED_CODES:
            return result
        path = args[0] if args else kwargs.get("path")
        if not path or "/login" in path or "/register" in path:
            return result
        kwargs["x_token"] = TOKEN
        return fn(*args, **kwargs)
    return wrapper


upstream_get = _fallback(upstream_get)
upstream_post = _fallback(upstream_post)
upstream_post_raw = _fallback(upstream_post_raw)

_orig_play_payload = play_payload


def play_payload(vid, part, x_token=None):
    result = _orig_play_payload(vid, part, x_token)
    if result:
        return result
    path = "/pc/video/play?id=%s&play=mp4&part=%s" % (vid, urllib.parse.quote(part))
    o = upstream_get(path, x_token=x_token)
    if isinstance(o, dict) and (
        o.get("code") in (403101, 403501) or "尚未购买" in str(o.get("message", ""))
    ):
        buy = upstream_post(
            "/pc/video/buy",
            {"id": int(vid), "part": part, "play": "mp4"},
            x_token=x_token,
        )
        if buy.get("code") == 20000:
            return _orig_play_payload(vid, part, x_token)
    return result

def main():
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8765))
    host = os.environ.get("BIND", "127.0.0.1")
    if host != "0.0.0.0" and port_in_use(port):
        print("jcy backend already running on port %d" % port, flush=True)
        return
    server = http.server.ThreadingHTTPServer((host, port), Handler)
    print("jcy backend on http://%s:%d" % (host, port), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()