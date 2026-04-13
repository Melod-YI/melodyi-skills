---
name: cross-repo-analyzer
description: 用于在当前workspace下添加新的git项目，对比多个git项目的差异点时使用。
---

# cross-repo-analyzer

## 概述

按用户要求在当前workspace下拉取多个git项目（一般是同类的项目），之后如果客户需要分析某些技术特性在各个项目上的异同时，为每个项目运行claude并把用户的问题注入提示词，再把每个claude的输出汇总并进行对比展示。

claude执行可能耗时较久，你可以多留一些timeout冗余(20分钟以上)，并且通过并行执行来节省时间。

## 目录格式

```
current_workspace/
├── git-repo1
├── git-repo2
└── ...
```

## 使用场景

### 场景一：添加新的git项目

如果客户要求添加新的git项目，
1. 在当前工作目录执行 git pull命令拉取对应的项目。
2. 检查拉取到的项目中，是否已经有CLAUDE.md或者Agent.md文件。
3. 如果第二条中发现没有此类文件，则按下述命令执行

```bash
CLAUDE_CODE_GIT_BASH_PATH="C:\Applications\Scoop\apps\git\current\bin\bash.exe" powershell -Command "cd '项目路径'; claude -p --permission-mode acceptEdits '/init'"
```

在windows下需要严格按照上述命令执行，如果有异常应该联系用户而不是自己尝试修改。  这个命令解决了环境变量，一些git bash的命令差异，以及init命令时的写入权限。

### 场景二：更新git

当用户要求更新时，为所有的项目执行git命令获取最新的更新。

### 场景三：对比分析

如果客户询问要对比或分析某个特性，例如“对比下各个项目是如何做xxxx的”、“各家在xxx方面有什么异同”、“分析下各个项目xxx”等场景。你需要到各个项目目录下执行命令，拉起一个claude code来在各个项目里进行分析。

**需要注意，你不应该使用子agent，而是使用bash的方式实现，以确保子agent的系统提示词、工具与默认的claude code一致。**

命令示例
```bash
CLAUDE_CODE_GIT_BASH_PATH="C:\Applications\Scoop\apps\git\current\bin\bash.exe" powershell -Command "cd '项目路径'; claude -p '用户想确认的问题'"
```

你应该优化用户的原始问题提示词，与用户确认理解是否一致后，用优化的提示词去让claude分析。

当获取到所有的返回后，你需要汇总整理后再呈现给用户。

除非用户说明，否则默认对比分析要作用于当前目录下的所有项目。例如，如果用户先让你添加项目，再让你对比分析，你需要找到目录下的所有项目（包括之前已经存在的项目），而不是只分析新添加的项目。

### 场景四：进一步分析

如果客户对你的问题还有疑问，提出了更具体的问题，那么需要让claude继续分析。你需要在调用claude的时候添加 -c 指令来恢复上一次的对话内容。

这些问题可能指定了只在某些项目内运行。那么你只需要在用户指定的项目内执行命令。

示例命令
```bash
CLAUDE_CODE_GIT_BASH_PATH="C:\Applications\Scoop\apps\git\current\bin\bash.exe" powershell -Command "cd '项目路径'; claude -p -c '用户想确认的问题'"
```

你依旧需要等各个项目返回后，汇总整理再呈现给用户。

**需要注意，如果当前时一个新对话的第一个问题，或者用户问了一个和之前无关的问题，那么应该是场景二而不是场景三**
