import norfetools as Dplt
from norfetools import plt
import numpy as np

plt.figure(figsize=(3,3))
plt.plot([0, 1, 2, 3, 4], [0, 1, 4, 9, 16],label="test $\phi$")  # 示例图表
plt.xlabel(r"test x $x^{12345}=y_{\mathrm{min}-\text{test}}$ test $\phi_{i,j,\mu}$")
Dplt.Set_axis_formatting('both', nbins=6, decimals=0)  # 设置x轴和y轴
plt.legend()
Dplt.SaveFig(2, "test", )