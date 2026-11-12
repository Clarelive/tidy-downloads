# 短视频 004《骂完就进步，是骂有用吗？》

这个分支只放这一条短视频的成片、封面、出片代码和发布文案，和 tidy-downloads 本身的代码无关（那些在 `main` 分支）。

- 成片：`抖音号/videos/004_骂完就进步/out/004_骂完就进步_v2.mp4`（竖屏 1080×1920，36.2 秒）
- 封面：同一个文件夹里的两张 PNG
- 标题、简介和每句话的依据：`抖音号/videos/004_骂完就进步/发布.md`
- 仿真：`抖音号/videos/004_骂完就进步/sim/sim.py`（1000 个孩子考两次试；`result.json` 是画面用的那一遍，`稳健性_200遍.json` 是跑 200 遍的范围）
- 画面：`抖音号/videos/004_骂完就进步/scene.html`；声音：`抖音号/videos/004_骂完就进步/sound.py`

重新出片要有 Node、Playwright、Python（numpy）和 ffmpeg：先在 `抖音号/engine/` 里 `npm install`，再在 `抖音号/` 里运行
`node engine/render.js videos/004_骂完就进步/scene.html videos/004_骂完就进步/out/frames`，然后在片子文件夹里跑 `python3 sound.py`，最后用 ffmpeg 把帧和 `out/mix.wav` 合成。

内容由 AI 生成。
