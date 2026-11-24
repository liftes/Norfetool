# NorfeDraw

**NorfeDraw** 是一个专为科学绘图场景设计的 Python 工具包，基于 `matplotlib` 提供风格一致、结构清晰的图像绘制与保存接口，并封装了常用的颜色设置、坐标轴格式化、色条美化与临时数据存储等功能，适用于科研作图、论文投稿和教学展示。

---

## 📦 功能概览

### 🎨 绘图样式与风格管理

- `Set_style(styles)`: 使用上下文管理器临时设置 `matplotlib` 的绘图风格（如 `science`, `nature`, `grid`）。
- 全局使用 `science` 风格，并调整了网格透明度、图例样式等默认参数以提升图像美感。

### 📁 图像保存与展示

- `Save_Fig(flag, path, filepath="figure/")`：根据 `flag` 控制是否保存或显示图像：
  - 若为 `True`：保存为指定路径；
  - 若为 `False`：调用 `plt.show()` 展示图像；
  - 若为 `2`（int）：保存为 `png/svg`，并在备用风格下再保存一轮（带 `_altstyle` 后缀）。

### 🎨 颜色与样式展示

- `SetColor(cmap_name, num_colors, extract_first_colors=False, ifshow=False)`  
  生成一组可用颜色列表，可从 colormap 中提取前若干颜色或均匀采样。

- `TestColorList(color_list)`  
  以图形方式展示颜色在不同曲线和点图中的表现。

### 🧭 坐标轴与色条美化

- `Set_axis_formatting(axis, nbins, decimals)`  
  设置 x/y 轴主刻度数量和显示精度（小数点位数）。

- `Set_colorbar_ticks_outward(cbar, ...)`  
  设置 colorbar 主/子刻度线向外，支持自定义长度和宽度。

- `Set_colorbar_ticks_inward(cbar, ...)`  
  设置 colorbar 主/子刻度线向内，支持自定义长度和宽度。

### 💾 临时数据缓存与恢复

- `Save_data(obj, filename='temp_data_list.pkl')`  
  使用 `pickle` 保存任意 Python 对象到文件。

- `Load_data(filename='temp_data_list.pkl')`  
  从文件加载对象。

- `Ensure_directory_exists(filename)`  
  自动创建目标文件路径所需的目录结构。

---

## 🔧 快速使用示例

```python
import matplotlib.pyplot as plt
import numpy as np
from norfetools import SaveFig, SetColor

x = np.linspace(0, 2 * np.pi, 100)
colors = SetColor("viridis", 3)

for i, c in enumerate(colors):
    plt.plot(x, np.sin((i + 1) * x), color=c, label=f"f{i}")

plt.legend()
SaveFig(2, "sin_demo.png")  # 保存为多格式，包含两种风格
```

---

## 🧰 内置工具类说明

本项目提供 `Sl`、`Bib` 和 `TexBuild` 工具类，分别用于文件操作、参考文献清理和 LaTeX 编译。它们为项目的自动化、批处理和投稿准备提供便利支持。

---

### 🗂️ `Sl` 类：文件路径与文本替换工具

`Sl` 提供简单但实用的文件路径管理与批量替换功能，适用于模板处理、路径初始化等场景。

#### 🔹 `Sl.ensure_directory_exists(file_path)`
确保文件保存路径存在，若文件已存在则删除。

- **参数**：
  - `file_path (str)`: 文件的完整保存路径。

- **功能**：
  - 自动创建中间目录；
  - 如果文件已存在则先删除。

#### 🔹 `Sl.replace_strings_in_file(file_name, replace_dict, new_file_path)`
对文件内容中出现的特定字符串进行替换，并写入新路径。

- **参数**：
  - `file_name (str)`: 要读取的原始文件；
  - `replace_dict (dict)`: 要替换的映射，如 `{ "旧字符串": "新字符串" }`；
  - `new_file_path (str)`: 替换后内容的输出文件路径。

- **典型用途**：
  - 自动替换 `.tex` 模板变量；
  - 批量更新路径、注释、符号等源文件内容。

---

### 📚 `Bib` 类：LaTeX Bib 文件清理与引用提取工具

`Bib` 类适用于从实际使用的 `.tex` 文件中提取 `\cite{}` 引用项，并自动从 `.bib` 文献数据库中筛选对应条目、删除冗余字段、规范作者与期刊格式，生成精简版 `.bib` 文件，适合论文投稿使用。

#### 🔹 `Bib.generate_clean_bib(input_bib_path, tex_files, output_bib_path)`
主函数，自动完成从 `.tex` 中提取引用、筛选 `.bib` 条目、清理格式并输出。

- **参数**：
  - `input_bib_path (str)`: 原始 `.bib` 文件；
  - `tex_files (List[str])`: 所有使用到的 `.tex` 文件路径；
  - `output_bib_path (str)`: 清理后 `.bib` 文件保存路径。

#### 🔹 `Bib.find_all_tex_files(root_dir)`
递归查找某目录下所有 `.tex` 文件，返回路径列表。

#### 🔹 `Bib.replace_inline_math(tex_file_list)`
将 `\(...\)` 替换为 `$...$`，用于 LaTeX 中的行内数学语法统一。

---

#### ✨ Bib 文件清理的核心特点：

- ✂️ **字段精简**：移除无关字段如 `abstract`, `file`, `keywords`, `isbn` 等；
- 🧑‍🔬 **作者格式统一**：将 `{Last, First}` 格式转为 `First Last`，并清除多余大括号；
- 📰 **期刊名智能格式化**：
  - 特定缩写如 `JACS`, `PNAS`, `IEEE` 保持全大写；
  - 常用介词如 `of`, `in`, `and` 保持小写；
  - 其余单词首字母大写。

---

#### 🧪 示例：

```python
from norfetools import Bib

tex_files = Bib.find_all_tex_files("manuscript/")
Bib.generate_clean_bib("library.bib", tex_files, "cleaned.bib")
```


---

## LaTeX 双版本构建：`TexBuild`（1.6.0）

Python 3.9 及以上；真实编译另需 TeX Live/MiKTeX、`latexmk` 和对应引擎。
模块不改写 tex 文件，不会在导入时自动编译，也不需要新 Python 依赖。

```python
from norfetools import TexBuild

result = TexBuild.build(
    texRootDir=r"C:\YourProject\Article",
    texFiles=["Manuscript.tex", "SupportingInformation.tex"],
    rtorTex="response/ResponsetoReviewers.tex",  # 可省略，默认 None
    engine="pdflatex",
    rtorEngine="xelatex",
    buildDir="build",                         # 默认值，可省略
    dryRun=True,                              # 先返回命令计划；False 才编译
)

for entry in result["commands"]:
    print(entry["cwd"], entry["command"])
```

列表形式为同一批主文件生成清洁版和高亮版；也可以分别指定：

```python
texFiles = {
    "clean": ["Manuscript.tex", "SupportingInformation.tex"],
    "highlighted": ["Manuscript.tex"],
}
```

只传一个模式即可只生成该版。各模式的主文件名（不含后缀）不能重复；最终 PDF 名称也不能冲突。
路径相对显式的 `texRootDir` 解析，各主 tex 从自身目录编译，保留图片、子文件及 bib 的相对路径。
默认正式输出如下，辅助文件分别保存在 `build/clean`、`build/highlighted` 和 `build/response`：

```text
build/Manuscript.pdf
build/SupportingInformation.pdf
build/HighlightedManuscript.pdf
build/HighlightedSupportingInformation.pdf
build/ResponsetoReviewers.pdf
```

1.6.0 新增可选参数 `flatOutput` 和 `highlightedPrefix`；不传时保留上述目录结构和命名。
若希望所有 PDF 和编译辅助文件直接产生在 `build`，高亮版使用小写前缀：

```python
result = TexBuild.build(
    texRootDir=r"C:\YourProject\Article",
    texFiles=["Manuscript.tex", "SupportingInformation.tex"],
    rtorTex="response/ResponsetoReviewers.tex",
    buildDir="build",
    flatOutput=True,
    highlightedPrefix="highlighted",
)
```

此时高亮版的 PDF、AUX、BBL 和日志统一使用 `highlightedManuscript` 等任务名，
不再创建 `clean`、`highlighted`、`response` 子目录，也不依赖旧目录中的数据。
前缀允许英文字母、数字、连字符和下划线；名称冲突会在编译前报错。
平铺构建通过任务名区分主 AUX；若源文件使用 `\include`，还须自行区分两版的子 AUX 文件名。
当前常用的 `\input` 子文件不生成独立 AUX，不受此限制。

正文等文件先交替构建，直到所选主文件的 AUX 标签稳定；可用 `maxRounds` 调整上限（默认 6）。
RtoR 最后编译，要求此次包含高亮模式，其页码/行号应读取高亮版的数据。
最终检查 PDF/AUX/日志存在，以及常见的未定义引用、文献和重复标签警告。
默认分目录模式在所有请求的编译成功后才复制正式 PDF；平铺模式直接写入最终位置。
这些检查不是对引用内容正确性的审查。
`result["outputs"]` 按模式和文件名返回 PDF 的 `Path`，`result["response"]` 返回可选回复 PDF；
`result["compiled"]` 表示是否实际完成编译。失败抛出异常，由调用脚本处理，不调用 `sys.exit()`。

### TeX 源文件配合约定

默认向正文/SI 注入 `\ntbuildmode`（清洁 0、高亮 1）、`\ntauxdir`（当前模式的 AUX 目录）、
`\ntauxprefix`（当前 AUX 任务名前缀）和 `\ntpdfprefix`（最终 PDF 前缀）。
分目录模式的 AUX 前缀为空，平铺高亮版则使用 `highlightedPrefix`。
源文件必须识别相应开关，不能假定任意 tex 都会自动出现修订颜色。可以用 `modeDefinitions`
覆盖模式的 TeX 前置代码，例如 `{"clean": r"\def\showchanges{0}", "highlighted": r"\def\showchanges{1}"}`；
目录和前缀仍会自动注入。正文引用 SI 的示例：

```tex
\providecommand{\ntauxdir}{./build}
\providecommand{\ntauxprefix}{}
\providecommand{\ntpdfprefix}{}
\externaldocument[SI-]{\ntauxdir/\ntauxprefix SupportingInformation}[\ntpdfprefix SupportingInformation.pdf]
```

RtoR 接收 `\ntresponseauxdir` 和 `\ntresponseauxprefix`，始终指向高亮版的 AUX。
在其导言区配置：

```tex
\providecommand{\ntresponseauxdir}{../build/highlighted}
\providecommand{\ntresponseauxprefix}{}
\externaldocument[M-]{\ntresponseauxdir/\ntresponseauxprefix Manuscript}
\externaldocument[SI-]{\ntresponseauxdir/\ntresponseauxprefix SupportingInformation}
```

以上须配合项目已有的 `xr`/`xr-hyper` 设置。模块不会自动修改这些引用。
项目使用的 `.sty`、`.cls` 和宏仍随论文源码保留，不依赖已安装的 Python 包来供 TeX 查找。
辅助目录名称不支持 `%`、花括号、`^^` 或换行；含空格及通常的项目 `#` 路径可保留。
引擎支持 `pdflatex`、`xelatex`、`lualatex`，可通过 `latexmk` 参数指定可执行文件。

### 本地打包和发布

```powershell
python -m build
python -m twine check dist/norfetool-1.6.0.tar.gz dist/norfetool-1.6.0-py3-none-any.whl
python -m twine upload --repository pypi dist/norfetool-1.6.0.tar.gz dist/norfetool-1.6.0-py3-none-any.whl
```

上传时按提示输入用户名 `__token__` 和项目的 PyPI API token；不要将 token 写进脚本或命令行。
只上传本轮两个文件，避免将 `dist` 中保留的旧版本一起上传。
