# 混合版 8 GB（VIctory-NVIDIA 分支 × cool_fox × 8 GB 补丁）

本仓库是 [trustno1-coder/VIctory-NVIDIA](https://github.com/trustno1-coder/VIctory-NVIDIA)
（VIctory 的 N 卡分支）这一路线下的分支：代码树取自其下游
[codec-d/cool_fox](https://github.com/codec-d/cool_fox) 的 `f4b48ad`
（*Publish the pareto-residency Windows build and portable launcher*），
再加一组**针对 8 GB 显存显卡**的补丁。运行方式、开关组合与上游一致，
只多一个 `VICTORY_TEXTURE_DROP_MIPS`。

**仓库内不含任何游戏文件、代码或素材**，运行时全部来自你自己的 Xbox dump。
许可证沿用上游 **GPL-3.0-or-later**。

---

## 一、为什么叫"混合版"

它是两支的混合体。一条线是 [VIctory-NVIDIA](https://github.com/trustno1-coder/VIctory-NVIDIA)
（N 卡分支，把 4K 锁死的主线改成能出画、能测性能的一支）：Wave32 lowering、
N 卡视图堆上限、`VICTORY_OWN_UPSCALER` 那套渲染缩放都出自这条线。
另一条线是 [VIctory](https://github.com/Marvisak/VIctory) 的 AMD RDNA 3 分支
（`codec-d/cool_fox`），它把 N 卡那边的 Wave32 lowering、movie-plane 平滑上传、
XMA 音频修复、32 GB 常驻预算一并移植了进来（`8cc31ab`），并自带
pareto-residency 开关组。本分支在它之上再叠一层 8 GB 显存适配，
三条线混在一起跑，故称混合版。

## 二、相对上游的改动（代码 8 个文件，+897 −14；文档与工具另计）

| 文件 | 改动 |
|---|---|
| `crates/victory-gpu/src/resource.rs` | 新增 `drop_levels` / `dropped` / `host_subresource` / `title_subresources` / `readback_subresource` / `shift_levels`；tile 路径对丢层纹理让路；`held_only` 的起始层从丢层数开始 |
| `crates/victory-gpu/src/texture.rs` | `Staging` 记录 `drop` / `first_mip` / `title_bytes`；`staging_layout` 把上传源收缩到保留层（保留原 tiled 偏移与 tail 放置）；detile 用 `mip + first_mip`；`alias` 拒绝丢层数不同的拷贝 |
| `crates/victory-gpu/src/list.rs` | 拷贝 / 回读 / resolve 按 host 子资源重新编号；丢层数不同的纹理之间跳过拷贝 |
| `crates/victory-gpu/src/descriptor/host.rs` | 着色器视图的起始层、层数、最小层钳制随丢层数平移 |
| `apps/victory/src/translate.rs` | 预热（`warm`）路径跟随上述层映射 |
| `crates/victory-shader/src/emit/lower.rs` | `scrub_nan`：NaN 与 ±∞ 换 0（`VICTORY_NAN_SCRUB`）；`with_loose_lds`：单 digest 的实验 wave64 翻译 |
| `crates/victory-shader/src/emit/mod.rs` | 上述两个开关的接入点（实验那个按 digest `50cf2832…` 命中） |
| `crates/victory-gpu/src/shader_cache.rs` | `VICTORY_NAN_SCRUB` 进 shader 缓存键 |

**动机**（写在 `drop_levels` 的注释里）：N 卡上按索引挑选纹理时，内存预算先到，
而排队等着的还有约 15 000 张；每帧 GPU 时间会翻三倍（上游在 RTX 4060 Ti 首房间的
测量）。丢掉每张纹理最大的若干 mip 层，每层约省掉 3/4 字节。

**代价**：丢层后着色器看到的是缩小后的纹理（每层边长减半、`shift_levels` 负责把
视图对齐到同一批 texel），远处细节会糊。`VICTORY_TEXTURE_DROP_MIPS=0`（默认）关掉，
与上游行为完全一致。

只对满足以下条件的纹理生效：title 自己填充的 2D 纹理、至少 512 texel、
边长能被 `4 << N` 整除、至少 5 层 mip、非多重采样。数组纹理暂不处理。

另有两个**默认关闭**的着色器开关（`crates/victory-shader/src/emit/`）：

| 开关 | 作用 |
|---|---|
| `VICTORY_NAN_SCRUB=1` | 像素着色器写出的颜色、f32 图像存储里，NaN 与 ±∞ 一律改 0。一个坏值进 bloom/模糊/时序超分会扩散成留在历史里的黑色块（N 卡上脸与空气中的黑斑）；∞ 反过来把画面漂白。不同于主机行为，故做成开关 |
| `VICTORY_EXPERIMENTAL_WAVE_02384=1` | 只对 digest `50cf2832…` 一个程序生效：允许分支内无序的跨半 wave LDS 读写再翻译。半 wave 可能看到过期 LDS 值，不是精确的 wave64 翻译，**仅供这一个程序** |

`VICTORY_NAN_SCRUB` 进了 shader 缓存键（`victory-gpu/src/shader_cache.rs`），
开关改变后不会吃到旧缓存的翻译；实验 wave 那个只按 digest 命中一个程序，暂未进键。

## 三、构建

需要 Windows 10/11 x64、AVX2 CPU、支持 SM 6.6 + mesh shader 的 D3D12 显卡、
pinned Rust 工具链（1.88）、MSVC C++ 生成工具与 Windows SDK。

```powershell
cargo build --release --locked -p victory                 # target\release\victory.exe
cargo build --locked --profile diag -p victory --features diagnostics   # target\diag\victory.exe
```

diag 构建自带诊断浮层与更多日志，本身慢 10–15%，别拿它当性能基准。

## 四、运行

```powershell
$env:VICTORY_GAME_DIR = 'D:\Games\MyDump'   # 你自己的 dump，必须有 game_scarlett_master.exe
.\tools\launch-hybrid.ps1                   # release + Series S + 8 GB 开关组
.\tools\launch-hybrid.ps1 -Diag -Hud -Seconds 600
.\tools\launch-hybrid.ps1 -DropMips 0       # 关掉丢层，等于上游行为
```

`tools/launch-hybrid.ps1` 做的就是把下面这组环境变量设好再交给
`tools/run_ab.py`；后者负责起进程、挂 HUD、自动点过账户进世界、每 25 秒截图。

也可以完全手动：

```powershell
$env:CONSOLE='series-s'; $env:VICTORY_TEXTURE_DROP_MIPS='1'
.\target\release\victory.exe run $env:VICTORY_GAME_DIR\game_scarlett_master.exe --execute --console series-s
```

## 五、开关

| 变量 | 值 | 作用 |
|---|---|---|
| `CONSOLE` | `series-s` | Series S 档，输出 1080p 而不是 2160p（8 GB 卡唯一的活路） |
| `VICTORY_TEXTURE_DROP_MIPS` | 0–4 | **本分支新增**。host 拷贝丢掉最大的 N 层 mip，每层约省 3/4 纹理字节；视图自动平移 |
| `VICTORY_THIN` | 1 | 精简 host 列表 |
| `VICTORY_JOIN_PARTS` / `VICTORY_JOIN_COPIES` | 8 / 1 | 合并列表与拷贝，减少提交次数 |
| `VICTORY_RELAY` / `VICTORY_RELAY_COPY` | 2 / 1 | 经中继缓冲区搬运 |
| `VICTORY_CARD_STEPS` / `VICTORY_CARD_AWAKE` | 2 / 1 | 卡侧执行步骤与唤醒 |
| `VICTORY_SHOW_AFTER` | 1 | 上传那一批提交完成后再让槽位看见新纹理（否则按索引读到未完成的纹理，会页错误） |
| `VICTORY_TEXTURE_NO_WAIT` | 1 | 不等待纹理上传完成 |
| `VICTORY_UPLOAD_AHEAD` / `VICTORY_LEVELS_ON_DEMAND` | 1 / 1 | 提前上传、mip 按需上传 |
| `VICTORY_INDIRECT_WINDOW` / `VICTORY_INDIRECT_BATCH` | 1 / 2 | indirect 参数的窗口校验与批处理 |
| `VICTORY_MAP_THREADS` | 1 | 多线程映射 |
| `VICTORY_AMBIENT` / `VICTORY_AMBIENT_AIR` | 0.8 / 1.5 | 没有光追时的亮度补偿 |
| `VICTORY_CARD_BUFFERS_MIN_KB` | 64 | 小缓冲留在显存 |
| `VICTORY_NAN_SCRUB` | 0/1 | 颜色与 f32 图像存储里的 NaN/±∞ 换 0，治 N 卡上的黑斑与漂白（默认关，见第二节） |

其余上游开关见 `victory.example.toml` 与 `docs/`。

## 六、本机实测（i9-14900HX / RTX 4060 Laptop 8 GB / 2×16 GB DDR5-5600 / 31.6 GB / Win 11 26300）

全部 Series S 档、1920×1080 输出，数字取自 `ab/*.log` 里 `X fps, Y ms/frame` 行的中位数
（只统计 draws > 1000 的世界内帧）：

| 构建 | 场景 | 中位帧率 | 帧时间 | draws | 索引纹理上传 |
|---|---|---|---|---|---|
| 上游 cool_fox release，`DROP_MIPS=0` | 世界内 | **2.70** | 370 ms | ~4470 | 0.31 MB/张 |
| 本分支 release，`DROP_MIPS=1` | 世界内（更重） | **2.40** | 417 ms | ~6050 | **0.11 MB/张** |
| 本分支 diag + D3D12 调试层，`DROP_MIPS=1` | 世界内 | 2.40 | 417 ms | ~4820 | 0.11 MB/张 |
| 本分支 release | 菜单 / 加载 | 30.0 | 33 ms | 7–10 | — |
| 早期 N 卡分支（不在本仓库），Series S + `RENDER_SCALE=0.5` | 世界内 | **7.70** | 130 ms | ~4920 | — |

怎么读这几行：

- 丢层确实生效：每张"按索引上传"的纹理从 0.31 MB 降到 0.11 MB（约 1/2.8，
  与丢掉最大一层 = 省掉约 3/4 字节吻合），上传总量 4.9 GB → 8.3 GB 是因为这一轮
  场景更重、纹理张数从 1.6 万涨到 7.6 万。
- **但帧数没涨**。两轮 draws 差 35%（4470 vs 6050），不是同场景 A/B，不能直接相减；
  同场景 `DROP_MIPS=0/1/3` 的对照还在跑，跑完补进来。
- 7.70 fps 那行是早期 N 卡分支靠 **`RENDER_SCALE=0.5` 降低渲染分辨率**（540p 世界 +
  游戏超分到 1080p）才做到的，不是代码更快。这台机器 1080p 真渲染的世界内就是 2–3 fps。
- **参考系 CGBJ**（= codec-d/cool_fox，本仓库直接上游）：PortWatch 评分条目里写明
  NVIDIA 平台「8GB 系统内存 + **16 GB 显存**」平均 25 fps、渲染率 0.85（同样是压渲染
  分辨率）、稳定性 0.85，仍有轻微视觉故障、稳不住 30。本仓库在其上做 8 GB 显存适配。
- **建议用 ≥ 12 GB 显存的卡验证丢层补丁**：8 GB 卡显存本身就是瓶颈（打满后 1.2–1.4 万个
  纹理槽在等显存），丢层省下的显存副本会被其它瓶颈吃掉，测不出补丁真实收益。
- 瓶颈不是算力：上游自述私有内存 40–46 GB、建议 64 GB，本机 31.6 GB，
  显存 8 GB 同时打满，页面文件与显存在 PCIe 上来回搬；日志里
  `the card has no room for more; they wait` 的纹理槽峰值 1.2–1.4 万个。
- 8 GB 补丁改的是"纹理驻留"这层（省下的是显存里的副本），目前还没换来帧数，
  别把它当性能补丁读。

## 七、已知问题

- 丢层会让远处纹理变糊，重场景下比不丢层更明显；它是拿画质换显存。
- 数组纹理与多重采样纹理不走丢层路径。
- 有 D3D12 调试层时日志里大量 `id=538` / `id=646` 状态告警，来自 title 自己的
  用法，release 构建同样存在，不影响出画。
- 窗口必须先置顶再点鼠标，否则点击落到别的窗口，游戏停在 10 draws。

## 八、上游与出处

- 主线分支：<https://github.com/trustno1-coder/VIctory-NVIDIA>（N 卡专用，本分支的来路）
- 直接上游：<https://github.com/codec-d/cool_fox>（`f4b48ad`，代码树取自这里）；
  在 PortWatch 的评分条目里它叫 **CGBJ**，当前 91.5% 可玩。
- 再上游：<https://github.com/Marvisak/VIctory>、<https://github.com/avatarmanz/VIctory-7900XTX>
- 许可：GPL-3.0-or-later（见 `LICENSE`）
