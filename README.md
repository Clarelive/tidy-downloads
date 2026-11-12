# 短视频 004《骂完就进步，是骂有用吗？》

**要发布这条视频，只看一个文件夹：`抖音号/videos/004_骂完就进步/发布包/`，先读里面的 `发布步骤.md`。**
成片、标题、简介、话题、三张封面和一份机器可读的清单（`发布.json`）都在那个文件夹里。

这个分支只放这一条短视频的东西，和 tidy-downloads 本身的代码无关（那些在 `main` 分支）。

**给 grok 的任务在 `给grok/` 文件夹里**，一个文件一件事，照文件里写的做。

## 其他文件
- 文案的来源和每句话的依据：`抖音号/videos/004_骂完就进步/发布.md`（发布包是照它生成的）
- 仿真：`抖音号/videos/004_骂完就进步/sim/sim.py`（1000 个孩子考两次试；`result.json` 是画面用的那一遍，`稳健性_200遍.json` 是跑 200 遍的范围）
- 画面：`抖音号/videos/004_骂完就进步/scene.html`；声音：`抖音号/videos/004_骂完就进步/sound.py`
- 出片和打包的脚本：`抖音号/engine/`

重新出片要有 Node、Playwright、Python（numpy）和 ffmpeg：先在 `抖音号/engine/` 里 `npm install`，再在 `抖音号/` 里运行
`node engine/render.js videos/004_骂完就进步/scene.html videos/004_骂完就进步/out/frames`，然后在片子文件夹里跑 `python3 sound.py`，用 ffmpeg 把帧和 `out/mix.wav` 合成，最后 `python3 engine/make_kit.py videos/004_骂完就进步` 重新生成发布包。

内容由 AI 生成。
