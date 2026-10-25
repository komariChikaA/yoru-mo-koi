# yoru-mo-koi

「夜もすがら君恋ふ」MAD 的 Godot、Storybrew 工程与全片视频渲染器。

## 作者说明

以下内容全部为工程性描述，笔记见：[「夜もすがら君恋ふ」制作过程及感想](https://komarichikaa.github.io/my-notes/posts/yomosugara-storybrew)。

## 工程

- 根目录 `*.cs`、`scriptslibrary/`、`.sbrew/`、`project.sbrew.yaml`：Storybrew 分镜、工具类与生产参数。
- `godot/`：神户街景、CG 木偶试验、副歌第三至第五镜与手机分镜的六个独立 Godot 工程。
- `assets/`：布局、路径、网格和素材来源等文本数据。
- `tools/`：原工程的素材处理及镜头导出脚本；使用前按本地环境设置输入和输出路径。
- `renderer/`：从同一批 Storybrew 精灵输出视频与原生 OSB，并支持打包 OSZ。

## 准备素材

仓库提供源码、场景、Shader、参数与布局数据。原作 CG、立绘、游戏素材、字体文件、音轨和生成帧保留在本地，路径维持工程中的相对引用。运行 Godot 前需恢复各工程 `assets/` 中引用的资源；运行 Storybrew 或渲染器前需准备已有的 osu! 谱面目录（含 `sb/` 素材、一个 `.osu` 和其音轨）。素材记录里的 `${GAME_ROOT}`、`${EAGLE_ROOT}`、`${REFERENCE_ROOT}` 表示本地来源根目录，不包含这些目录的内容。

第四镜重建发束还需在 `godot/chorus-four/local-assets/rebuilt-hair/` 放置 `CGC14/stage-cliff-wind-v2/` 与 `CGC15/stage-reference-wind-root-clean/` 的本地修复底图、发束和 `stage.json`，或调用 `configure` 时传入自己的 stage 目录。没有素材的源码检出不能直接完整播放。

## Storybrew 与视频导出

需要 Windows、.NET 8、Storybrew 1.96，以及已加入 PATH 的 FFmpeg / ffprobe。Godot 分镜使用 Godot 4.7.2。Storybrew DLL 使用本地安装，不随仓库分发。

在仓库根目录执行：

```powershell
$env:STORYBREW_HOME = 'C:/Tools/storybrew.1.96'
Copy-Item .sbrew/user.example.yaml .sbrew/user.yaml
# 修改 .sbrew/user.yaml 的 MapsetPath，指向已准备好的本地谱面目录。
dotnet build scripts.csproj --nologo
dotnet build renderer/full-export.csproj --nologo
dotnet renderer/bin/Debug/net8.0-windows/full-export.dll --fps 24 --bitrate 50M --out output
```

默认视频为 1920×1080、24fps、全片约 111.625 秒，H.264 + AAC。渲染器读取 `.sbrew` 可见性与图层顺序，应用原生 Storybrew 运动；Godot 镜头使用谱面中已安装的序列帧。`--export-only` 只输出 OSB 和素材引用；`--start`、`--end` 使用毫秒，可用于短段渲染。更多参数见 [渲染器说明](renderer/README.md)。

## OSZ 下载与实测

压缩版 Storyboard 已发布至 [Release v1.0.0](https://github.com/komariChikaA/yoru-mo-koi/releases/tag/v1.0.0)，OSZ 内已加入当前封面。

在 osu!lazer 下实测，RTX 2060 运行压缩版 Storyboard 播放流畅，没有明显卡顿。

压缩工作包括大纹理缩小、逐轴缩放补偿以及 OSB 指令精简；具体参数与压缩结果见 Release 说明。
