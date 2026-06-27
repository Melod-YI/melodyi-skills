## 输出目录结构（Jellyfin 规范）

```
Shows/剧名 (年) [tmdbid-xxx]/Season 01/剧名 (年) S01E01.mkv
Movies/电影名 (年) [tmdbid-xxx]/电影名 (年).mkv
```

- Season 文件夹写 `Season 01`（不写 `S01`）
- 多集合并：`S01E01-E02.mkv`；分段：`S01E01-part-1.mkv`
- 特别篇：`Season 00`
- 目标路径会做归一化：去尾斜杠、转平台原生分隔符，输入带不带斜杠均一致