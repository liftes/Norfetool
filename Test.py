import norfetools as Dplt
from norfetools import CreateFigure
from norfetools import plt
import numpy as np

# # plt.figure(figsize=(3,3))
# plt.plot([0, 1, 2, 3, 4], [0, 1, 4, 9, 16],label="test $\phi$")  # 示例图表
# plt.xlabel(r"test x $x^{12345}=y_{\mathrm{min}-\text{test}}$ test $\phi_{i,j,\mu}$")
# Dplt.Set_axis_formatting('both', nbins=6, decimals=0)  # 设置x轴和y轴
# plt.legend()
# Dplt.SaveFig(2, "test", )


import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

fig, ax, cax, layoutInfo = Dplt.CreateFigure(
    axesWidthCm=6.5,
    axesHeightCm=4.0,
    nRows=1,
    nCols=1,
    colorbarMode="right",
    colorbarWidthCm=0.30,
    colorbarGapCm=0.20,
    colorbarAlign="full",
)

# 造一点测试数据
x = np.linspace(0, 10, 200)
y = np.sin(x)

# 在主图上画线和散点
ax.plot(x, y, lw=1.0)
ax.scatter(x[::12], y[::12], s=10)

ax.set_xlabel("x")
ax.set_ylabel("y")
ax.set_title("CreateFigure test")

# 构造一个假的 colorbar
norm = mpl.colors.Normalize(vmin=0, vmax=1)
sm = mpl.cm.ScalarMappable(norm=norm, cmap="viridis")
sm.set_array([])

cbar = fig.colorbar(sm, cax=cax, orientation="vertical")
cbar.set_label("Test Colorbar")

# 打印尺寸信息，检查是否符合预期
print(layoutInfo)

plt.show()