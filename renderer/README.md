# 全片视频渲染器

在仓库根目录先设置 `STORYBREW_HOME`、准备 `.sbrew/user.yaml` 和本地谱面素材，再构建 `scripts.csproj` 与 `renderer/full-export.csproj`。

```powershell
dotnet renderer/bin/Debug/net8.0-windows/full-export.dll --fps 24 --bitrate 50M --out output
# 短段验证（时间单位为毫秒）
dotnet renderer/bin/Debug/net8.0-windows/full-export.dll --start 19000 --end 20000 --out output/sample
```

`--project` 指定工程根目录，默认当前目录；`--dll` 指定已构建的 Storybrew 脚本，默认 `bin/Debug/net8.0-windows/storyboard.dll`。支持 `--start`、`--end`、`--fps`、`--width`、`--height`、`--bitrate`、`--crf`、`--threads`、`--export-only`。

工具应用 `.sbrew` 配置和原生 Storybrew 曲线，通过 OpenTK 在隐藏 GPU 窗口合成，再交由 FFmpeg 编码。`export.json` 记录图层、精灵、纹理引用和源谱面。

`python renderer/package.py output` 可压缩 OSB 并打包本地 OSZ；`--install` 会写入所选本地谱面，并保存被替换 OSB 的备份。压缩器拒绝 loop/trigger，导出器拒绝 Animation。打包检查只覆盖引用、ZIP 条目、CRC 和 OSB 字节一致性。已发布压缩版的 osu!lazer / RTX 2060 实测结果见[主 README](../README.md#osz-下载与实测)。
