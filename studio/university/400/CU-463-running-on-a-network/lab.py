# CU-463 lab: a port of the decisions in server.py at v0.43.0. EXPECTED holds the status codes from running the real middleware functions on mocked aiohttp requests. This lab checks the port against them. No network. The port does not look up host names other than localhost.
import re
def split_host(h):
    m = re.match(r"^(?:\[([^\]]+)\]|([^:]+))(?::(\d+))?$", h.lower()); return (m.group(1) or m.group(2)), m.group(3)
def origin_parts(o):
    m = re.match(r"^[a-z]+://([^/]*)", o.lower()); netloc = m.group(1); host, port = split_host(netloc); return netloc, host, port
def is_loopback(host): return host == "localhost" or host == "::1" or host.startswith("127.")
def origin_only(host, origin, sec_fetch_site):
    if sec_fetch_site == "cross-site": return 403
    if host and origin:
        host_domain = host.lower(); netloc, o_host, o_port = origin_parts(origin); origin_domain = netloc; h_host, h_port = split_host(host_domain)
        if o_port is None: host_domain = h_host
        if h_port is None: origin_domain = o_host
        if is_loopback(h_host) and host_domain != origin_domain: return 403
    return 200
def with_cors(host, origin, sec_fetch_site): return 200
CASES = [("a script, no Origin", "127.0.0.1:8188", None, None, 200, 200),
 ("the page itself", "127.0.0.1:8188", "http://127.0.0.1:8188", "same-origin", 200, 200),
 ("another site, modern browser", "127.0.0.1:8188", "https://evil.example", "cross-site", 403, 200),
 ("another site, no Sec-Fetch-Site", "127.0.0.1:8188", "https://evil.example", None, 403, 200),
 ("another site, LAN address, no Sec-Fetch-Site", "203.0.113.20:8188", "https://evil.example", None, 200, 200),
 ("another site, LAN address, modern browser", "203.0.113.20:8188", "https://evil.example", "cross-site", 403, 200),
 ("a script faking any Origin, LAN address", "203.0.113.20:8188", "http://anything.example", None, 200, 200),
 ("sibling subdomain, public name", "comfy.example.com", "https://other.example.com", "same-site", 200, 200),
 ("localhost page calling 127.0.0.1 name", "localhost:8188", "http://127.0.0.1:8188", None, 403, 200)]
print(f"{'POST /prompt from':46} {'default':>8} {'with CORS':>10}")
for name, h, o, s, a, b in CASES:
    x = origin_only(h, o, s); y = with_cors(h, o, s); print(f"{name:46} {x:8} {y:10}"); assert (x, y) == (a, b), name
print()
def middlewares(enable_cors=None, offline=False, enable_manager=False):
    m = ["cache_control", "deprecation_warning"]
    m.append("cors" if enable_cors else "origin_only")
    if offline: m.append("block_external")
    if enable_manager: m.append("manager")
    return m
print("default:     ", middlewares()); print("--enable-cors-header:", middlewares("*")); assert "origin_only" not in middlewares("*")
print()
def bind(listen="127.0.0.1"): return listen.split(",")
print("no flag:        ", bind()); print("--listen alone: ", bind("0.0.0.0,::")); assert bind("0.0.0.0,::") == ["0.0.0.0", "::"]
def scheme(keyfile, certfile): return "https" if keyfile and certfile else "http"
print("only --tls-keyfile:", scheme("k", None), "  both:", scheme("k", "c")); assert scheme("k", None) == "http"; print()
USERS = {"anna_1": "anna", "bo_2": "bo"}
def user_id(multi, header):
    u = "default"
    if multi and header is not None:
        u = header
        if u.startswith("__"): raise KeyError("Unknown user: " + u)
    if multi and u not in USERS: raise KeyError("Unknown user: " + u)
    return u
print("--multi-user, header says anna_1:", user_id(True, "anna_1"), " (no password asked)"); print("no --multi-user, header ignored:", user_id(False, "anna_1")); assert user_id(True, "bo_2") == "bo_2"
