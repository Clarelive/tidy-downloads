"""照 发布.md 生成发布包：发布的人或机器人只用看 <片子文件夹>/发布包/。

用法（在 抖音号/ 里运行）：python3 engine/make_kit.py videos/004_骂完就进步

读：<片子文件夹>/发布.md（标题、简介正文、话题、置顶评论、发布设置、成片和封面的路径）
写：<片子文件夹>/发布包/  成片、封面、标题.txt、简介.txt、置顶评论_可选.txt、发布.json、发布步骤.md
检查不过就报错停下：标题超过 30 字、简介超过 1000 字、话题不是 # 开头、文件不存在。
"""
import hashlib, json, os, re, shutil, subprocess, sys

TITLE_MAX, DESC_MAX = 30, 1000   # 抖音网页端的上限


def sections(md):
    out, name = {}, None
    for line in md.split("\n"):
        m = re.match(r"^## (.+?)\s*$", line)
        if m:
            name = m.group(1); out[name] = []
        elif name:
            out[name].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def bullets(text):
    d = {}
    for line in text.split("\n"):
        m = re.match(r"^- (.+?)：(.+)$", line.strip())
        if m: d[m.group(1)] = m.group(2).strip()
    return d


def video_info(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    w, hh = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", err).groups()
    fps = re.search(r"([\d.]+) fps", err).group(1)
    return dict(width=int(w), height=int(hh), seconds=round(int(h) * 3600 + int(m) * 60 + float(s), 1), fps=float(fps),
                size_bytes=os.path.getsize(path), sha256=hashlib.sha256(open(path, "rb").read()).hexdigest())


def main(folder):
    sec = sections(open(os.path.join(folder, "发布.md"), encoding="utf-8").read())
    files = bullets(sec["成片和封面"]); settings = bullets(sec["发布设置"])
    title = sec["标题"].split("\n")[0].strip()
    body = sec["简介正文"]
    topics = sec["话题"].split()
    pinned = sec["置顶评论"].split("\n\n", 1)[1].strip()      # 第一段是说明，第二段起才是要发的字
    assert all(t.startswith("#") and len(t) > 1 for t in topics), "话题要写成 #话题，用空格隔开"
    desc = body + "\n" + " ".join(topics)
    assert len(title) <= TITLE_MAX, f"标题 {len(title)} 字，超过 {TITLE_MAX}"
    assert len(desc) <= DESC_MAX, f"简介 {len(desc)} 字，超过 {DESC_MAX}"

    kit = os.path.join(folder, "发布包"); shutil.rmtree(kit, ignore_errors=True); os.makedirs(kit)
    names = {}
    for key, rel in files.items():
        src = os.path.join(folder, rel); assert os.path.isfile(src), f"找不到 {rel}"
        names[key] = os.path.basename(rel); shutil.copy2(src, os.path.join(kit, names[key]))
    info = video_info(os.path.join(kit, names["成片"]))
    mmss = "%02d:%02d" % divmod(int(info["seconds"]), 60)

    def write(name, text):
        open(os.path.join(kit, name), "w", encoding="utf-8", newline="\n").write(text.rstrip("\n") + "\n")
    write("标题.txt", title); write("简介.txt", desc); write("置顶评论_可选.txt", pinned)
    manifest = {
        "id": os.path.basename(folder.rstrip("/")).split("_")[0],
        "video": names["成片"], "video_info": info,
        "title": title, "description": desc, "description_body": body, "topics": [t.lstrip("#") for t in topics],
        "covers": {"vertical_3x4": names["竖封面 3:4"], "horizontal_4x3": names["横封面 4:3"], "full_9x16": names["整屏封面 9:16"]},
        "ai_declaration": settings["声明"], "visibility": settings["谁可以看"], "allow_save": settings["允许保存"] == "允许",
        "cross_post": settings["同时发布到其他平台"] != "不同时发布", "location_hotspot_collection": None,
        "suggested_time": settings["建议时间"], "suggested_time_note": settings.get("时间说明", ""),
        "pinned_comment_optional": pinned,
        "limits": {"title_max": TITLE_MAX, "title_len": len(title), "description_max": DESC_MAX, "description_len": len(desc)},
    }
    write("发布.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    first = body.split("\n")[0]
    write("发布步骤.md", f"""# {manifest["id"]} 怎么发（给发布的人或机器人）

这个文件夹里的东西齐了就能发，不用再找别的文件。字段以 `发布.json` 为准；`标题.txt`、`简介.txt` 是同样的内容，方便整段复制。

## 文件
| 文件 | 用在哪 |
|---|---|
| `{names["成片"]}` | 要发的视频：竖屏 {info["width"]}×{info["height"]}，{info["seconds"]} 秒 |
| `标题.txt` | 作品标题，{len(title)} 字（上限 {TITLE_MAX}） |
| `简介.txt` | 作品简介，{len(desc)} 字（上限 {DESC_MAX}），最后一行是 {len(topics)} 个话题 |
| `{names["竖封面 3:4"]}` | 竖封面 |
| `{names["横封面 4:3"]}` | 横封面 |
| `{names["整屏封面 9:16"]}` | 只能选整屏封面时用 |
| `置顶评论_可选.txt` | 可选，号主说要才发 |

## 步骤
1. 上传 `{names["成片"]}`。传完核对时长显示 {mmss}。
2. 标题：贴 `标题.txt` 的全文。
3. 简介：贴 `简介.txt` 的全文，段落之间的空行要保留。
   - 最后一行的话题如果没有变成话题（没有变色、点不动），把那一行删掉，改成一个一个输入：{"、".join("`" + t + "`" for t in topics)}，每个后面跟一个空格。
   - 只有一个描述框、没有单独的标题框时：第一行贴标题，空一行，再贴简介。
4. 封面：能上传封面就传竖封面和横封面；只能从视频里选一帧时，用第一帧。
5. 声明：在“自主声明”（手机端叫“作品声明”）里选“{settings["声明"]}”。这一项必须选。
6. 其他设置：{settings["谁可以看"]}；允许保存；不同时发布到其他平台；位置、热点、合集都不填。
7. 发布前再核一遍四样：标题；简介第一句是“{first}”；声明已选；时长 {mmss}。
8. 发布。建议时间：{settings["建议时间"]}。{settings.get("时间说明", "")}

## 不要做的
- 只做发布这一件事：不点赞、不关注、不评论、不私信、不改账号资料。
- 碰到验证码、扫码登录、风险提示就停下，交给号主本人。
- 发布失败最多再试 1 次；还不行就停，把页面上的提示原文带回来。
- 置顶评论不要自己决定发，号主明确说要才发。

## 发完带回来的
- 发布时间（精确到分钟）和作品链接；
- 内容管理里的状态：审核中、已发布，还是没通过；
- 话题有没有变成能点的链接；
- 发布满 24 小时、72 小时各读一次：播放、点赞、评论、分享、收藏、完播率、2 秒跳出率、涨粉，和评论原文。
""")
    print(f"发布包：{kit}")
    for n in sorted(os.listdir(kit)): print("  %9d  %s" % (os.path.getsize(os.path.join(kit, n)), n))
    print(f"标题 {len(title)}/{TITLE_MAX} 字；简介 {len(desc)}/{DESC_MAX} 字；视频 {info['seconds']} 秒")


if __name__ == "__main__":
    main(sys.argv[1])
