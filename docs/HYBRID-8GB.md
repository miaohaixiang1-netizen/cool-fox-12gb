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

## 二、相对上游的改动（5 个文件，+824 −11）

| 文件 | 改动 |
|---|---|
| `crates/victory-gpu/src/resource.rs` | 新增 `drop_levels` / `dropped` / `host_subresource` / `title_subresources` / `readback_subresource` / `shift_levels`；tile 路径对丢层纹理让路；`held_only` 的起始层从丢层数开始 |
| `crates/victory-gpu/src/texture.rs` | `Staging` 记录 `drop` / `first_mip` / `title_bytes`；`staging_layout` 把上传源收缩到保留层（保留原 tiled 偏移与 tail 放置）；detile 用 `mip + first_mip`；`alias` 拒绝丢层数不同的拷贝 |
| `crates/victory-gpu/src/list.rs` | 拷贝 / 回读 / resolve 按 host 子资源重新编号；丢层数不同的纹理之间跳过拷贝 |
| `crates/victory-gpu/src/descriptor/host.rs` | 着色器视图的起始层、层数、最小层钳制随丢层数平移 |
| `apps/victory/src/translate.rs` | 预热（`warm`）路径跟随上述层映射 |

**动机**（写在 `drop_levels` 的注释里）：N 卡上按索引挑选纹理时，内存预算先到，
而排队等着的还有约 15 000 张；每帧 GPU 时间会翻三倍（上游在 RTX 4060 Ti 首房间的
测量）。丢掉每张纹理最大的若干 mip 层，每层约省掉 3/4 字节。

**代价**：丢层后着色器看到的是缩小后的纹理（每层边长减半、`shift_levels` 负责把
视图对齐到同一批 texel），远处细节会糊。`VICTORY_TEXTURE_DROP_MIPS=0`（默认）关掉，
与上游行为完全一致。

只对满足以下条件的纹理生效：title 自己填充的 2D 纹理、至少 512 texel、
边长能被 `4 << N` 整除、至少 5 层 mip、非多重采样。数组纹理暂不处理。

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

其余上游开关见 `victory.example.toml` 与 `docs/`。

## 六、本机实测（i9-14900HX / RTX 4060 Laptop 8 GB / 2×16 GB DDR5-5600 / 31.6 GB）

全部为 Series S 档、1920×1080 输出：

| 构建 | 场景 | 帧率 | 帧时间 | draws | 备注 |
|---|---|---|---|---|---|
| 上游 cool_fox release | 世界内 | 2.6–3.2 | 377–385 ms | 4465 | 未开丢层 |
| 本分支 diag + D3D12 调试层 | 世界内 | 2.1–2.2 | 446–465 ms | 4747 | 调试层本身就大幅拖慢，不是基准 |
| 本分支 release | 菜单 / 加载 | 30 | 33.3 ms | 7–10 | 上限，不代表世界内 |

这台机器的瓶颈不在算力而在内存：上游自述私有内存 40–46 GB、建议 64 GB，
本机只有 31.6 GB，页面文件与显存在 PCIe 上来回搬，这才是 2–3 fps 的直接原因。
8 GB 补丁针对的正是这一层（纹理驻留），但目前还没有干净的 release 世界内
A/B 数字，等跑完再补。

## 七、已知问题

- 丢层会让远处纹理变糊，重场景下比不丢层更明显；它是拿画质换显存。
- 数组纹理与多重采样纹理不走丢层路径。
- 有 D3D12 调试层时日志里大量 `id=538` / `id=646` 状态告警，来自 title 自己的
  用法，release 构建同样存在，不影响出画。
- 窗口必须先置顶再点鼠标，否则点击落到别的窗口，游戏停在 10 draws。

## 八、上游与出处

- 主线分支：<https://github.com/trustno1-coder/VIctory-NVIDIA>（N 卡专用，本分支的来路）
- 直接上游：<https://github.com/codec-d/cool_fox>（`f4b48ad`，代码树取自这里）
- 再上游：<https://github.com/Marvisak/VIctory>、<https://github.com/avatarmanz/VIctory-7900XTX>
- 许可：GPL-3.0-or-later（见 `LICENSE`）
