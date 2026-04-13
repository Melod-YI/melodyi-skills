---
name: arxiv-analyze
description: Use this skill when asked to read an arxiv paper given an arxiv URL or an an arxiv code.
---

# arXiv Paper Analysis Skill

Analyze arXiv papers by reading the TeX source content, handling referenced elements (figures, tables, equations).

## Input Processing

Accept these formats, all converted to TeX Source URL:

| Input | Conversion |
|-------|------------|
| `2603.28052` | `https://arxiv.org/src/2603.28052` |
| `https://arxiv.org/abs/2603.28052` | `https://arxiv.org/src/2603.28052` |
| `https://arxiv.org/src/2603.28052` | Use directly |

## Working Directory Convention

Files are organized by paper ID:

```
.arxiv_papers/<paper_id>/
├── source.tar.gz     # Downloaded archive
└── source/           # Extracted TeX files
```

## Core Workflow: Content-Driven Analysis

The analysis starts by reading the main TeX file and follows references to handle figures, tables, and other elements.

### Step 1: Download and Extract

```bash
mkdir -p .arxiv_papers/<paper_id>/source
curl -L -o .arxiv_papers/<paper_id>/source.tar.gz "https://arxiv.org/src/<paper_id>"
tar -xzf .arxiv_papers/<paper_id>/source.tar.gz -C .arxiv_papers/<paper_id>/source
```

### Step 2: Locate Main File

List the extracted files to find the main TeX file:

```bash
ls .arxiv_papers/<paper_id>/source/
```

Common main file names: `main.tex`, `arxiv.tex`, `paper.tex`, or matching the paper title.

### Step 3: Read Main Content

Once you've found the main file, Read the contents and then recurse through all other relevant source files to read the paper.

你必须处理过所有的外部资源，确保对论文的内容有准确、完整的了解。所有图片必须经过图像理解工具的处理。

## Handling Referenced Elements

When you encounter references in the TeX source, process them inline:

### Figures (External Files)

`\includegraphics{figures/example.pdf}` or `\includegraphics{images/chart.png}`

**For PNG/JPG/WebP files:**
1. Note the figure context from surrounding text and `\caption{}`
2. Construct a focused prompt based on what information you need
3. Call an available image understanding tool with the file path and prompt

**For PDF files:**
1. Use Read tool on the PDF to extract text labels (axis, legend, caption)
2. Convert to PNG using the bundled script:
   ```bash
   python .claude/skills/arxiv-analyze/scripts/convert_pdf_to_png.py <pdf_path>
   ```
   The PNG is saved alongside the PDF (same directory).
3. Call image understanding tool with the converted PNG path and a prompt built from step 1 labels + context

### Tables (External Files)

`\input{tables/results.tex}`

1. Read the referenced `.tex` file
2. Parse the LaTeX table structure (`\begin{tabular}`, columns, rows)
3. Present as readable Markdown table to the user
4. Explain key findings from the data

### TikZ Diagrams (Embedded)

`\begin{tikzpicture}...`

Already in the TeX source you're reading. Parse directly:
1. Interpret `\node` definitions (boxes, labels, positions)
2. Interpret `\draw` connections (arrows, flow)
3. Present as ASCII/Markdown flowchart with explanations

### Math Commands (External Files)

`\input{math_commands.tex}`

If custom math macros are defined externally, read that file first to understand notation like `\ours{}`, `\methodname{}`, etc.

## Step 4: Report

你的目标是帮用户更深入的理解这个论文的原理，你的输出是对论文的解释、重点介绍、补充、价值判断、展望等，而并非仅是对论文进行简单的概括总结。

输出的阶段应该使用中文。

在满足下述的要求的前提下，再根据你觉得重要的部分进行补充。

### 说明论文的逻辑链路

你需要输出完整的逻辑链路，例如作者发现了什么问题、根据什么现象提出了假设或者创新、是通过什么样的科学实验或者统计或者数学推导来进行验证的、最后的结果是如何的。

对于关键的片段，可以先直接提供原文相关片段的译文，再给出自己的通俗解释。

对于科学实验或者统计。你除了需要详细介绍流程和结果外，还需要用通俗的方式介绍为什么这个实验或者统计能够佐证作者的想法，本身是否足够严谨和客观。实验的介绍需要足够详细，背景、对比参照物等都介绍到。

对于数学计算和推导。你无需展开过程，仅对关键的节点和推导结果做出专业且通俗的解释。

### 给出你的评论

你需要给出你对论文价值的判断，客观公正地描述论文的优点、价值、局限性。

你需要结合当前业界技术发展的现状，给出你对这篇论文的未来影响的判断。例如研究方向、应用前景、技术走势、重要程度、关键影响、如何落地等等方面。描述未来的影响与应用阶段的困难。

你需要进行泛化思考，考虑论文在其他领域的关联性。其中我们重点关注AI、Agent、计算机软硬件、云服务、软件架构与工程、消费级电子终端等领域。

## Bundled Script

| Script | Purpose |
|--------|---------|
| `scripts/convert_pdf_to_png.py` | Convert a single PDF to PNG (saved in same directory) |

**Usage:**
```bash
python scripts/convert_pdf_to_png.py <pdf_path> [dpi]
```

**Output:** PNG file(s) saved alongside the PDF, path(s) printed to stdout.

**Dependencies:** PyMuPDF (`pip install PyMuPDF`)

## Tips

1. **Follow references naturally** — Don't preprocess all files; handle them when encountered in the main text
2. **Note image directory names** — Papers may use `figures/`, `images/`, `fig/`, or other names
3. **Build prompts from context** — Use `\caption{}`, surrounding paragraphs, and extracted labels to create focused image analysis prompts
4. **Tables are LaTeX source** — Read and parse directly; no conversion needed
5. **TikZ is inline** — Parse the code when you encounter it in the main text