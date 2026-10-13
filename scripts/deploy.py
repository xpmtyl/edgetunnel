#!/usr/bin/env python3
"""把 edgetunnel 的 _worker.js 部署到 Cloudflare Worker。

直连 Cloudflare REST API，不依赖 npm / wrangler。

关键：ES module 必须以 Content-Type: application/javascript+module 上传。
     否则 Cloudflare 会把脚本当「经典脚本」解析，文件里的 export 语句直接语法错误，
     运行时表现为 Error 1101 "Worker threw exception"（每个请求都 1101，且无法被
     用户代码 try/catch 捕获，因为模块根本没初始化成功）。

必需环境变量：
  CLOUDFLARE_API_TOKEN / CF_API_TOKEN
  CLOUDFLARE_ACCOUNT_ID / CF_ACCOUNT_ID
可选：
  WORKER_NAME   默认 edgetunnel
  COMPAT_DATE   默认 2025-11-04
  ADMIN         管理员密码 -> secret_text binding ADMIN
  PROXYIP       反代 IP    -> plain_text  binding ProxyIP
"""
import json
import os
import sys
import uuid
import urllib.error
import urllib.request

TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CF_API_TOKEN")
AID = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("CF_ACCOUNT_ID")
if not TOKEN or not AID:
    sys.exit("缺少 CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID")

SCRIPT = os.environ.get("WORKER_NAME", "edgetunnel")
COMPAT = os.environ.get("COMPAT_DATE", "2025-11-04")
ADMIN = (os.environ.get("ADMIN") or "").strip()
PROXYIP = (os.environ.get("PROXYIP") or "").strip()

here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(here, "_worker.js")
if not os.path.exists(src):
    sys.exit("找不到源文件: %s" % src)

js = open(src, "rb").read()
print("source : %s (%d bytes)" % (src, len(js)))
print("worker : %s | account: %s | compat: %s" % (SCRIPT, AID, COMPAT))

bindings = []
if ADMIN:
    bindings.append({"type": "secret_text", "name": "ADMIN", "text": ADMIN})
if PROXYIP:
    bindings.append({"type": "plain_text", "name": "ProxyIP", "text": PROXYIP})
desc = ", ".join(
    "%s=%s(%s)" % (b["name"], "***" if b["type"] == "secret_text" else b["text"], b["type"])
    for b in bindings
) or "(无)"
print("binding: %s" % desc)

meta = {"main_module": "_worker.js", "compatibility_date": COMPAT}
if bindings:
    meta["bindings"] = bindings

boundary = "----edgetunnel" + uuid.uuid4().hex


def field(name, value, ctype=None, filename=None):
    head = 'Content-Disposition: form-data; name="%s"' % name
    if filename:
        head += '; filename="%s"' % filename
    part = b"--" + boundary.encode() + b"\r\n" + head.encode()
    if ctype:
        part += b"\r\nContent-Type: " + ctype.encode()
    return part + b"\r\n\r\n" + value + b"\r\n"


payload = b""
payload += field("metadata", json.dumps(meta).encode(), "application/json")
payload += field("_worker.js", js, "application/javascript+module", "_worker.js")
payload += b"--" + boundary.encode() + b"--\r\n"

url = "https://api.cloudflare.com/client/v4/accounts/%s/workers/scripts/%s" % (AID, SCRIPT)
r = urllib.request.Request(url, data=payload, method="PUT", headers={
    "Authorization": "Bearer " + TOKEN,
    "Content-Type": "multipart/form-data; boundary=" + boundary,
})
try:
    with urllib.request.urlopen(r, timeout=300) as resp:
        d = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    sys.exit("部署失败 HTTP %s\n%s" % (e.code, e.read().decode()[:1500]))

if not d.get("success"):
    sys.exit("部署失败: %s" % json.dumps(d.get("errors"), ensure_ascii=False))

res = d.get("result") or {}
print("部署成功: id=%s modified=%s" % (res.get("id"), res.get("modified_on")))
