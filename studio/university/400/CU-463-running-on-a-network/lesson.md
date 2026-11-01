# CU-463 - Running ComfyUI safely on a network

**Objective.** Say exactly what `--listen`, `--enable-cors-header`, the TLS flags and `--multi-user` do and don't protect, and put ComfyUI behind a login of your own. Taught by Captain Graph.

## The idea

ComfyUI has no login. Its own routes, the ones listed below, ask for no password, token or proof of who you are. By default that's fine, because it only answers on 127.0.0.1, your own computer.

Its `SECURITY.md` says so directly: "Anyone with access to the ComfyUI URL is trusted". It also says that issues needing `--listen` are not treated as vulnerabilities: the user "has chosen to expose it and is responsible for securing that deployment (firewall, reverse proxy, authentication, etc.)".

So `--listen` isn't a setting that makes sharing safe. It only opens the door.

## What someone can do with the URL

These routes are all open to anyone who can reach the port. We read each one in `server.py`, `app/user_manager.py` and `internal_routes.py`.

| They can | With |
|---|---|
| Run any graph, as many as they like, and use your GPU | `POST /prompt` |
| Stop your job or empty your queue | `POST /interrupt`, `POST /queue` |
| Unload your models | `POST /free` |
| Read every past prompt, with its text | `GET /history` |
| Download your outputs and inputs, and list them | `GET /view`, `GET /internal/files/output` |
| Add files to your input folder, and overwrite them with `overwrite` | `POST /upload/image` |
| Read your saved workflows and settings, and change or delete them | `/userdata` |
| Read the server log, and your full folder paths | `GET /internal/logs`, `GET /internal/folder_paths` |
| See versions, memory, and the command line you started it with | `GET /system_stats` |
| See the queue, and take over a job's messages and previews with the client id that `GET /queue` lists | `GET /queue`, `GET /ws` |

This graph is harmless, and it shows the point. Whoever can reach your port can write this file to your output folder.

{{graph:a_save_preview}}

Some limits do hold. `/view` only serves the output, input and temp folders, and it refuses `..` in a file name. `SaveImage` refuses paths outside the output folder. Upload size is limited by `--max-upload-size`, 100 MB by default. Tokens for partner services, `auth_token_comfy_org` and `api_key_comfy_org`, are taken out before the prompt is stored. These are limits on paths and size, not on who may use the server. Custom nodes run as ordinary Python and can add routes of their own, so each one widens this list.

## Each flag

**`--listen`.** Sets the address. On its own, with no value, it's `0.0.0.0,::`, meaning all network interfaces, IPv4 and IPv6. Nothing else changes.

**`--enable-cors-header`.** Sets `Access-Control-Allow-Origin` to the value you give, or `*`. It also sets `Allow-Credentials: true`. The important part is what it removes. In `PromptServer.__init__` the choice is either-or: CORS on means the origin check is not installed at all.

**The origin check.** The default middleware. It exists so that a random web page can't post to your 127.0.0.1. It returns 403 if the browser says `Sec-Fetch-Site: cross-site`, or if the host is a loopback address and `Origin` doesn't match `Host`. It's a guard against browsers doing things for a web page, and nothing else. A script can send any headers it likes.

**`--tls-keyfile`, `--tls-certfile`.** Turns on HTTPS, which encrypts traffic. You need both, and with just one the server stays on plain HTTP. Nobody is asked who they are: the code sets `verify_mode=ssl.CERT_NONE`.

**`--multi-user`.** Gives each user separate storage. It picks the user from a `comfy-user` request header, and only checks that the user exists. There's no password, so anyone can send any name. It sorts files; it doesn't protect them.

**`--enable-manager`, `--enable-agent`.** These add more routes to the same server. We didn't read those packages, so read their documents before you open them to anyone.

## Try it

{{play:exposed}}

## Lab

We ran the real `create_origin_only_middleware` and `create_cors_middleware` from `server.py`, extracted without importing the rest, on mocked requests with no network. The lab holds those status codes, and asserts that a small port of the logic gives the same answers.

```text
POST /prompt from                               default  with CORS
a script, no Origin                                 200        200
the page itself                                     200        200
another site, modern browser                        403        200
another site, no Sec-Fetch-Site                     403        200
another site, LAN address, no Sec-Fetch-Site        200        200
another site, LAN address, modern browser           403        200
a script faking any Origin, LAN address             200        200
sibling subdomain, public name                      200        200
localhost page calling 127.0.0.1 name               403        200
```

Read it from the bottom of the default column upwards.

- A script always gets through. So does everything that isn't a browser.
- The `Origin` match only runs for loopback hosts. On a LAN address, it's only `Sec-Fetch-Site` that protects you. A browser that doesn't send the header gets through.
- Same-site is allowed. A page on a sibling subdomain of a public name can post.
- The last row is the false alarm: `localhost` and `127.0.0.1` differ, so a tool pointed at one from a page on the other gets 403.
- With CORS on, the whole right column is 200, with any origin value. Naming one origin only tells browsers which page may read replies. Nothing refuses the request. MDN's CORS guide explains that a simple POST, with a type like `text/plain`, needs no preflight, and `post_prompt` reads the body as JSON without checking the type. So a page you visit can still queue on your server, even though it can't read the answer.

What the flags install, and what they bind to:

```text
default:      ['cache_control', 'deprecation_warning', 'origin_only']
--enable-cors-header: ['cache_control', 'deprecation_warning', 'cors']
```

```text
no flag:         ['127.0.0.1']
--listen alone:  ['0.0.0.0', '::']
only --tls-keyfile: http   both: https
```

```text
--multi-user, header says anna_1: anna_1  (no password asked)
no --multi-user, header ignored: default
```

## A setup that holds up

These are our recommendations. We didn't test a particular proxy setup for this lesson.

1. Keep ComfyUI on 127.0.0.1, with no `--listen`.
2. If only you need to reach it from elsewhere, use a VPN or an SSH tunnel to your own machine.
3. If others must reach it, put a reverse proxy with a login and HTTPS in front. It needs to pass websocket upgrades for `/ws`.
4. Leave CORS off. If a tool truly needs it, name one origin, and know that this does not bring the origin check back.
5. If you need a real multi-tenant service, this isn't a setting. Give each tenant their own instance, or write a service that holds the keys, checks each graph and talks to ComfyUI itself.
6. Treat your custom nodes as part of what you expose. The `SECURITY.md` threat model excludes them.

## What goes wrong

- **"I set a password in the settings."** There's no such setting in the server. Anything that looks like one is in a pack, or a page. Check by sending a plain `GET /system_stats` from another device. If it answers, you're open.
- **A cloud machine with `--listen`.** Now it's on the internet, unless a firewall says otherwise. Check that from outside.
- **A tool says to add `--enable-cors-header`.** That turns off the check above, whatever value you give it. Turn it off when you finish, or serve the tool from the same address as ComfyUI.
- **HTTPS and feeling safe.** TLS keeps strangers from reading traffic. It doesn't stop them using your server.
- **`--tls-keyfile` alone.** The server runs on plain HTTP. Check the address it prints.
- **The API key in a graph.** A key typed into a text widget is a normal input. It goes into history and into your PNGs, and only the two named token fields are removed. Keep keys out of widgets.

## Sources

- [ComfyUI v0.43.0, SECURITY.md](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/SECURITY.md)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, app/user_manager.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/app/user_manager.py)
- [ComfyUI v0.43.0, internal_routes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/api_server/routes/internal/internal_routes.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, folder_paths.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/folder_paths.py)
- [MDN: Cross-Origin Resource Sharing (CORS)](https://github.com/mdn/content/blob/main/files/en-us/web/http/guides/cors/index.md)
