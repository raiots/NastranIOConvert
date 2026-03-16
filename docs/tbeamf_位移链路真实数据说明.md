# tbeamf 实际数据下的位移链路说明

本文基于一个真实梁模型算例的数据，核心输入包含两部分：

- 结构模型文本（BDF 片段）
- 位移结果文本（F06 中的 displacement vector 片段）

并且当前工具支持两种应变分量模式：

- `three_component`：3量（拉伸/面内弯曲/面外弯曲）
- `four_component`：4量（拉伸/扭转/面内弯曲/面外弯曲）

---

## 1. 原始数据处理

### 1.1 从 BDF 提炼出的结构信息

原始输入（结构模型文本，节选）：

```text
CBAR     10      1       1       2       0.      0.     1.
CBAR     11      1       2       3       0.      0.     1.
CBAR     12      1       3       4       0.      0.     1.
CBAR     13      1       4       5       0.      0.     1.
CBAR     14      1       5       6       0.      0.     1.
CBAR     15      1       6       7       0.      0.     1.
CBAR     16      1       7       8       0.      0.     1.
CBAR     17      1       8       9       0.      0.     1.
CBAR     18      1       9       10      0.      0.     1.
CBAR     19      1       10      11      0.      0.     1.

GRID     1               0.      0.      0.
GRID*    2                              .100000001490116 0.
*        0.
GRID*    3                              .200000002980232 0.
*        0.
GRID*    4                              .300000011920929 0.
*        0.
...
GRID*    10                             .899999976158142 0.
*        0.
GRID     11             1.       0.      0.
```

程序解析后得到：

- 节点数 `N = 11`（`GRID`）
- 结构边数 `E = 10`（`CBAR`）
- 节点 ID：`1 ~ 11`
- 拓扑：`1-2-3-...-11` 的连续梁

可提炼出的直接结果：

1. 几何坐标表 `grids(node_id, x, y, z)`
2. 连接关系表 `edges(node_i, node_j)`
3. 每条边长度（后续构造应变算子时计算）

本数据中，梁沿 `x` 方向，边长约为 `0.1`。

### 1.2 从 F06 displacement vector 提炼出的位移模态

原始输入（位移结果文本，节选）：

```text
D I S P L A C E M E N T   V E C T O R

             1      G      0.0            0.0            0.0            0.0            0.0            0.0
             2      G      0.0            0.0           -1.381695E-03   0.0            2.714286E-02   0.0
             3      G      0.0            0.0           -5.334819E-03   0.0            5.142858E-02   0.0
             4      G      0.0            0.0           -1.157366E-02   0.0            7.285715E-02   0.0
             5      G      0.0            0.0           -1.981250E-02   0.0            9.142858E-02   0.0
             6      G      0.0            0.0           -2.976562E-02   0.0            1.071429E-01   0.0
             7      G      0.0            0.0           -4.114732E-02   0.0            1.200000E-01   0.0
             8      G      0.0            0.0           -5.367187E-02   0.0            1.300000E-01   0.0
             9      G      0.0            0.0           -6.705357E-02   0.0            1.371429E-01   0.0
            10      G      0.0            0.0           -8.100669E-02   0.0            1.414286E-01   0.0
            11      G      0.0            0.0           -9.524553E-02   0.0            1.428572E-01   0.0
```

解析后（保留链路中使用的核心字段）得到：

- 模态数：`1`（解析结果名为 `Mode1`）
- 记录数：`11`
- 每节点字段：`ux, uy, uz, r1, r2, r3`

示例（解析后数据）：

| mode | node_id | ux | uy | uz | r1 | r2 | r3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Mode1 | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Mode1 | 2 | 0.0 | 0.0 | -1.381695e-03 | 0.0 | 2.714286e-02 | 0.0 |
| Mode1 | 3 | 0.0 | 0.0 | -5.334819e-03 | 0.0 | 5.142858e-02 | 0.0 |
| ... | ... | ... | ... | ... | ... | ... | ... |
| Mode1 | 11 | 0.0 | 0.0 | -9.524553e-02 | 0.0 | 1.428572e-01 | 0.0 |

可提炼出的直接结果：

1. 模态位移表 `displacements(mode, node_id, ux, uy, uz, r1, r2, r3)`
2. 每模态节点位移幅值统计，例如
   - `Mode1` 最大位移范数：`9.524553e-02`
3. 节点位移方向特征（本例平移几乎全在 `z` 方向）

---

## 2. 完整流程说明

以下对应核心链路：

```math
q \rightarrow \epsilon(=Bq) \rightarrow \epsilon_{scaled} \rightarrow q_{scaled}
```

最后按模态权重叠加平移位移得到组合变形场。

### 2.1 Step A：数据标准化与节点对齐

对每个模态，程序做一次 inner join：

```math
\text{joined} = \text{grids} \bowtie \text{displacements}
```

保留同时存在于 BDF 和位移文件中的节点。

本例结果：

- `Mode1` 对齐后节点数 `11`

产物：

- `joined(node_id, x, y, z, ux, uy, uz, r1, r2, r3)`

### 2.2 Step B：构造应变算子 $B$

本节符号：

- $i,j$：节点编号（例如边 $(1,2)$ 的两个端点）
- $\mathbf{x}_i=[x_i,y_i,z_i]^T$：节点 $i$ 的坐标
- $\mathbf{u}_i=[u_{xi},u_{yi},u_{zi}]^T$：节点 $i$ 的平移位移
- $\boldsymbol{\theta}_i=[r_{1i},r_{2i},r_{3i}]^T$：节点 $i$ 的转角
- $\mathbf{d}_{ij}=\mathbf{x}_j-\mathbf{x}_i$：边向量
- $L_{ij}=\lVert\mathbf{d}_{ij}\rVert_2$：边长
- $\mathbf{e}_1,\mathbf{e}_2,\mathbf{e}_3$：边局部正交基（$\mathbf{e}_1$ 沿边）

先计算几何量：

```math
\mathbf{d}_{ij}=\mathbf{x}_j-\mathbf{x}_i,\quad L_{ij}=\lVert\mathbf{d}_{ij}\rVert_2
```

然后按模式构造约束。

3量模式（拉伸/面内/面外）：

```math
\begin{aligned}
\epsilon_{ij}^{\text{stretch}} &= \frac{(\mathbf{u}_j-\mathbf{u}_i)\cdot\mathbf{e}_1}{L_{ij}},\\
\epsilon_{ij}^{\text{in-plane}} &= \frac{(\mathbf{u}_j-\mathbf{u}_i)\cdot\mathbf{e}_2}{L_{ij}},\\
\epsilon_{ij}^{\text{out-plane}} &= \frac{(\mathbf{u}_j-\mathbf{u}_i)\cdot\mathbf{e}_3}{L_{ij}}.
\end{aligned}
```

4量模式（拉伸/扭转/面内/面外）：

```math
\begin{aligned}
\epsilon_{ij}^{\text{stretch}} &= \frac{(\mathbf{u}_j-\mathbf{u}_i)\cdot\mathbf{e}_1}{L_{ij}},\\
\epsilon_{ij}^{\text{torsion}} &= \frac{(\boldsymbol{\theta}_j-\boldsymbol{\theta}_i)\cdot\mathbf{e}_1}{L_{ij}},\\
\epsilon_{ij}^{\text{in-plane}} &= \frac{(\mathbf{u}_j-\mathbf{u}_i)\cdot\mathbf{e}_2}{L_{ij}},\\
\epsilon_{ij}^{\text{out-plane}} &= \frac{(\mathbf{u}_j-\mathbf{u}_i)\cdot\mathbf{e}_3}{L_{ij}}.
\end{aligned}
```

堆叠后统一写成：

```math
\epsilon = Bq
```

维度关系：

- 3量模式：$q\in\mathbb{R}^{3N},\ \epsilon\in\mathbb{R}^{3E},\ B\in\mathbb{R}^{3E\times 3N}$
- 4量模式：$q\in\mathbb{R}^{6N},\ \epsilon\in\mathbb{R}^{4E},\ B\in\mathbb{R}^{4E\times 6N}$

本例（`N=11, E=10`）：

- 3量模式：`B` 尺寸为 `30 x 33`
- 4量模式：`B` 尺寸为 `40 x 66`

### 2.3 Step C：位移/转角转应变（原始）

构造原始自由度向量：

```math
q_{raw}=\begin{cases}
[u_{x1},u_{y1},u_{z1},\dots,u_{xN},u_{yN},u_{zN}]^T, & \text{3量模式}\\
[u_{x1},u_{y1},u_{z1},r_{11},r_{21},r_{31},\dots]^T, & \text{4量模式}
\end{cases}
```

并计算：

```math
\epsilon_{raw}=Bq_{raw}
```

本例统计（`Mode1`）：

- `max_abs_strain_raw = 0.142388`
- `max_stretch_raw = 0.0`
- `max_torsion_raw = 0.0`（4量模式统计项）
- `max_in_plane_bending_raw = 0.0`
- `max_out_plane_bending_raw = 0.142388`

### 2.4 Step D：应变放大

对每个模态给定放大倍数 $s_m$（UI 中的 `scale`）：

```math
\epsilon_{scaled}^{(m)}=s_m\cdot\epsilon_{raw}^{(m)}
```

本例（同一数据）实测比例关系：

- `scale=1.0`：最大位移 `0.095245530`
- `scale=2.0`：最大位移 `0.190491060`
- `scale=5.0`：最大位移 `0.476227650`

### 2.5 Step E：最小二乘反算自由度

反算目标：

```math
q_{scaled}=\arg\min_{q}\,\lVert Bq-\epsilon_{scaled}\rVert_2
```

为去除刚体不唯一性，首节点锚定：

- 3量模式：锚定 3 个自由度（`ux, uy, uz`）
- 4量模式：锚定 6 个自由度（`ux, uy, uz, r1, r2, r3`）

增广系统：

```math
\begin{bmatrix}
B\\
A
\end{bmatrix}q=
\begin{bmatrix}
\epsilon_{scaled}\\
0
\end{bmatrix}
```

本例（`Mode1`, `scale=1.0`）应变重构残差：

```math
\frac{\lVert Bq_{rec}-\epsilon_{raw}\rVert_2}{\lVert\epsilon_{raw}\rVert_2}\approx 2.207\times 10^{-14}
```

### 2.6 Step F：模态加权组合

若有多模态，按 `eta` 组合平移位移：

```math
\mathbf{u}_{comb}(i)=\sum_m \eta_m\,\mathbf{u}_{scaled}^{(m)}(i)
```

并输出位移模长：

```math
\mathrm{disp\_mag}(i)=\lVert\mathbf{u}_{comb}(i)\rVert_2
```

本例只有一个模态且默认 $\eta_1=1$，所以组合结果等于该模态结果。

---

## 3. 每一步输入/产物总览（本例）

1. 输入
- `tbeamf.bdf`
- `tbeamf.f06`
- 参数：`scale=1.0`, `eta=1.0`, `component_mode`（3量或4量）

2. 中间产物
- `model.grids`：11 节点
- `model.edges`：10 边
- `disp_df`：1 模态、11 条记录（含 `ux,uy,uz,r1,r2,r3`）
- 3量模式：`B=30x33`, `epsilon_raw` 长度 30, `q_scaled` 长度 33（11x3）
- 4量模式：`B=40x66`, `epsilon_raw` 长度 40, `q_scaled` 长度 66（11x6）

3. 最终产物
- `summary_df`：每模态统计（含 `max_torsion_raw`）
- `scaled_df`：
  - 3量模式：`node_id, ux, uy, uz, mode`
  - 4量模式：`node_id, ux, uy, uz, r1, r2, r3, mode`
- `edge_strain_df`：`stretch, torsion, in_plane_bending, out_plane_bending, strain`
- `combined_df`：加权组合后的平移位移场

---

## 4. 对这个数据可直接读出的结论

1. 结构是一维梁链式连接，平移位移主导方向为 `z`。
2. 当前样例中，扭转分量统计值接近 0。
3. 3量/4量两种模式都能稳定重构，且本例残差接近机器精度。
4. 在该样例上，`scale` 对输出位移幅值呈近线性放大。
