# 图生视频测试：汉小豚（匿名、免费、开源 I2V Space）

**结论：成功 1 段。** 用 Hugging Face 公开 Space **Lightricks/ltx-video-distilled**（LTX-Video distilled），匿名调用，没注册，没用 token。

## 输入
- 素材：官方素材包 `SAIGS01CompetitionMaterials.zip` → `中文/武汉SPU城市AI接待员虚拟形象.png`（1536×1024 三视图）。裁出最左边的正面像，放在 640×640 白底方图正中（没有提交到仓库）。
- 提示词：`a cute fluffy blue baby finless porpoise mascot standing at a hotel reception desk, it gets startled, eyes widen, body shakes, sweat drops, 3D Pixar style, soft lighting, static camera`
- 负面词：`worst quality, inconsistent motion, blurry, jittery, distorted`（Space 默认值）
- 参数：image-to-video，512×512，duration 3s，seed 42，guidance 1，improve_texture=True

## 输出：`ltx_distilled_test1.mp4`（Space 返回的原文件，没处理）
- 512×512，H.264，30fps，89 帧，**2.97 秒**，106 KB
- 排队+生成耗时：调用到返回共 **9.7 秒**，没有排队
- 抽帧观察（我只看了每秒 3 帧的截图，没看连续播放）：
  - 角色形象保持得很好：毛绒蓝色、腮红、大眼睛都在。
  - 自动生成了暖色酒店前台背景和台面。
  - 动作是身体从正面**转向侧面**再转回来一点。
  - **提示词里的"受惊、瞪眼、发抖、汗珠"基本没表现出来**。
  - 第一帧有一点白底到场景的过渡。
  - 有没有闪烁、抖动或变形，**无法判断**（没看连续播放）。

## 尝试过的 Space（共 3 个，按顺序）
| Space | 结果 |
|---|---|
| zerogpu-aoti/wan2-2-fp8da-aoti-faster（Wan2.2 I2V） | 失败：任务提交后约 2.5 秒被取消（CancelledError），Space 没返回具体原因。用原始 HTTP 接口重试返回 "404: Not Found"。没再重试 |
| multimodalart/wan2-1-fast（Wan2.1 I2V） | 失败：`You have exceeded your ZeroGPU runs limit. Authenticate with a Hugging Face token for more quota`。匿名配额用完，按要求没登录、没绕过 |
| Lightricks/ltx-video-distilled（LTX-Video） | **成功**（第一次因为传参格式错误报错；先上传图片再传服务器路径后成功） |

另外 Wan-AI/Wan2.1 官方 Space 状态是 RUNTIME_ERROR，Wan-AI/Wan2.2-5B 返回 401，都没调用。

## 备注
- ZeroGPU 的匿名配额是按 IP 或会话计算的，用完了需要 HF 账号 token。正式批量出片建议用自己的 HF 账号（免费账号也有每日配额），或者在本地/GPU 机器上跑开源权重。
- 想要"受惊"这类动作，可能要多试几个 seed、调高 guidance，或换 Wan2.2。这次只做了 1 段测试，没批量。
