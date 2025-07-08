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
from norfe_draw import SaveFig, SetColor

x = np.linspace(0, 2 * np.pi, 100)
colors = SetColor("viridis", 3)

for i, c in enumerate(colors):
    plt.plot(x, np.sin((i + 1) * x), color=c, label=f"f{i}")

plt.legend()
SaveFig(2, "sin_demo.png")  # 保存为多格式，包含两种风格
```

---

## 🧰 内置工具类说明

本项目包含两个内置类 `Sl` 和 `Bib`，分别用于通用文件操作与 `.bib` 文献文件的自动清理。它们为项目的自动化、批处理和投稿准备提供便利支持。

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
from Bib import Bib

tex_files = Bib.find_all_tex_files("manuscript/")
Bib.generate_clean_bib("library.bib", tex_files, "cleaned.bib")
```
