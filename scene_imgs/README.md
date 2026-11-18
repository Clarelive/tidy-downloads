# 场景/角色生图测试（免费、不登录）

## 服务尝试顺序
1. **Hugging Face Space black-forest-labs/FLUX.1-schnell**（匿名）：**失败**，返回 "You have exceeded your ZeroGPU runs limit. Authenticate with a Hugging Face token for more quota"。这和之前 LTX 用的是同一个匿名 ZeroGPU 配额（按 IP 计算），已经用完。按要求停下，没再找其他 ZeroGPU Space，因为它们共用同一个配额。
2. **image.pollinations.ai**（匿名 GET）：**能出图，但有限制**：
   - 请求了 `model=flux`、768×1344、`nologo=true`，但匿名用户**实际被换成了 `sana` 模型**（图片 EXIF 里写着 `actualModel: sana`），尺寸被降到 **580×1015**（仍是约 9:16 竖版）。
   - **右下角有 "pollinations.ai" 水印**，`nologo` 对匿名用户无效。

## Pollinations 条款（https://pollinations.ai/terms ，2026-11-17 版，2026-11-18 读取）
- 条款**没有**明确写生成图片归用户、可以商用。相关原文：
  - §8 IP & Open-Source："We and our licensors own the Service, models, and documentation. … **Model licences vary; verify before commercial use.**"
  - §3："Model outputs vary and may be … unsuitable for your intended use. You are responsible for reviewing outputs before relying on them."
  - §5 禁止侵权、规避限流。
- 实际用的 **Sana 模型**的许可证我没核实。我记得 NVIDIA Sana 早期权重是**非商用许可**（CC BY-NC-SA 4.0），但不确定 Pollinations 用的是哪个版本。**在确认之前，不建议把这些图用于参赛作品等公开/商业发布**，最多当构图参考。
- 带水印的图本身也不适合直接成片。

## 文件
（每张的提示词 = 下面的描述 + 统一风格词 "3D Pixar style animation still, soft warm morning sunlight, cozy, highly detailed, cinematic, vertical composition"）

| 文件 | 内容 | seed | 尺寸 | 服务/实际模型 | 观察（我看了图） |
|---|---|---|---|---|---|
| BG1_s1.jpg | 武汉老街早餐摊 | 11 | 580×1015 | pollinations / sana | 红砖老楼、桌椅，偏写实，不是皮克斯风；没有明显蒸汽；有水印；招牌位置有红底色块 |
| BG1_s2.jpg | 同上 | 22 | 580×1015 | pollinations / sana | 窄巷红砖，**有行人**（违反 no people），**有伪文字招牌**；偏写实；有水印 |
| BG2_s1.jpg | 老楼门口接待台 | 11 | 580×1015 | pollinations / sana | 红砖老楼侧面门廊，**没有接待台**，构图不是正面；偏写实；有水印 |
| BG2_s2.jpg | 同上 | 22 | 580×1015 | pollinations / sana | 正面红砖楼入口，有台阶和盆栽，**没有接待台**；门楣上有伪文字；有水印 |
| GM1_s1.jpg | 早餐摊大嗓门奶奶 | 11 | 580×1015 | pollinations / sana | 生成的是**年轻/中年短卷黑发女性**，不是灰发奶奶；**在微笑，不是张嘴大喊**；手里拿的东西不像勺子；背景不是纯色；偏写实；有水印 |

## 第 2 批中止
- GM1 seed 22 和 GM2 seed 11 返回 **HTTP 402 Payment Required**：Pollinations 匿名免费额度用完。按要求停下，没注册、没换 IP、没绕过。
- **GM1_s2、GM2_s1、GM2_s2 没有生成。**

## 小结
免费、不登录的两条路今天都撞到了配额。拿到的 5 张图都有这些问题：
- 偏写实，不是皮克斯风；
- 有水印；
- 用的模型商用许可不明；
- 好几张没按提示词来（有人、没接待台、奶奶不像奶奶）。

建议：
- 用户用自己的 Hugging Face 账号 token 调 FLUX.1-schnell（Apache-2.0），或者在本地/GPU 上跑 FLUX.1-schnell / SDXL；
- 角色图（奶奶）最好用同一 seed 加图生图，或者用 IP-Adapter 保持人物一致。
