# tbeamf 实际数据下的位移链路说明

本文基于一个真实梁模型算例的数据，核心输入包含两部分：

- 结构模型文本（BDF 片段）
- 位移结果文本（F06 中的 displacement vector 片段）

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
- 位移记录数：`11`
- 每个节点三向位移：`ux, uy, uz`

示例（原始位移）：

| mode | node_id | ux | uy | uz |
|---|---:|---:|---:|---:|
| Mode1 | 1 | 0.0 | 0.0 | 0.0 |
| Mode1 | 2 | 0.0 | 0.0 | -1.381695e-03 |
| Mode1 | 3 | 0.0 | 0.0 | -5.334819e-03 |
| ... | ... | ... | ... | ... |
| Mode1 | 11 | 0.0 | 0.0 | -9.524553e-02 |

可提炼出的直接结果：

1. 模态位移表 `displacements(mode, node_id, ux, uy, uz)`
2. 每模态节点位移幅值统计，例如
   - `Mode1` 最大位移范数：`9.524553e-02`
3. 节点位移方向特征（本例几乎全在 `z` 方向）

---

## 2. 完整流程说明

以下对应核心链路：

$$
u \rightarrow \epsilon(=Bu) \rightarrow \epsilon_{scaled} \rightarrow u_{scaled}
$$

并在最后做模态权重叠加。

### 2.1 Step A：数据标准化与节点对齐

对每个模态，程序做一次 inner join：

$$
\text{joined} = \text{grids} \bowtie \text{displacements}
$$

保留同时存在于 BDF 和位移文件中的节点。

本例结果：

- `Mode1` 对齐后节点数 `11`

产物：

- `joined(node_id, x, y, z, ux, uy, uz)`

### 2.2 Step B：构造应变算子 $B$

本节符号：

- $i,j$：节点编号（例如边 $(1,2)$ 中的两个端点）
- $\mathbf{x}_i=[x_i,y_i,z_i]^T$：节点 $i$ 的三维坐标
- $\mathbf{x}_j=[x_j,y_j,z_j]^T$：节点 $j$ 的三维坐标
- $\mathbf{u}_i=[u_{xi},u_{yi},u_{zi}]^T$：节点 $i$ 的三维位移
- $\mathbf{u}_j=[u_{xj},u_{yj},u_{zj}]^T$：节点 $j$ 的三维位移
- $\mathbf{d}_{ij}$：从节点 $i$ 指向节点 $j$ 的几何向量
- $L_{ij}$：边 $(i,j)$ 的长度
- $\mathbf{e}_1,\mathbf{e}_2,\mathbf{e}_3$：边的局部正交基
- $\epsilon_{ij}^{(k)}$：边 $(i,j)$ 在局部第 $k$ 个方向上的“位移梯度分量”

对每条边 $(i,j)$：

1. 计算边向量与长度：
$$
\mathbf{d}_{ij}=\mathbf{x}_j-\mathbf{x}_i,\quad L_{ij}=||\mathbf{d}_{ij}||
$$
其中：

- $\mathbf{x}_j-\mathbf{x}_i$ 就是“终点坐标减起点坐标”，得到边的方向与尺度
- $||\cdot||$ 是欧氏范数（向量长度），所以 $L_{ij}$ 是边长

2. 构造局部正交基 $\mathbf{e}_1,\mathbf{e}_2,\mathbf{e}_3$，其中 $\mathbf{e}_1$ 沿边方向。
解释：

- $\mathbf{e}_1=\mathbf{d}_{ij}/L_{ij}$（单位化后的边方向）
- $\mathbf{e}_2,\mathbf{e}_3$ 与 $\mathbf{e}_1$ 正交，且两两正交，长度都为 1
- 可以把它理解成“贴在这条边上的一个局部三维坐标系”

3. 分别沿三个方向写线性约束：
$$
\epsilon_{ij}^{(k)}=\frac{(\mathbf{u}_j-\mathbf{u}_i)\cdot\mathbf{e}_k}{L_{ij}},\quad k\in\{1,2,3\}
$$
解释：

- 先做位移差：$\Delta\mathbf{u}_{ij}=\mathbf{u}_j-\mathbf{u}_i$，表示这条边两端点的相对位移
- 再做点乘：$\Delta\mathbf{u}_{ij}\cdot\mathbf{e}_k$，得到相对位移在局部第 $k$ 方向上的投影（标量）
- 最后除以长度 $L_{ij}$：把“位移差”变成“沿边长度归一化后的梯度量”
- 因此 $\epsilon_{ij}^{(k)}$ 可以理解为：边 $(i,j)$ 在局部方向 $\mathbf{e}_k$ 上的离散应变/位移梯度

把三条约束按 $k=1,2,3$ 依次写出来就是：
$$
\epsilon_{ij}^{(1)}=\frac{(\mathbf{u}_j-\mathbf{u}_i)\cdot\mathbf{e}_1}{L_{ij}},\quad
\epsilon_{ij}^{(2)}=\frac{(\mathbf{u}_j-\mathbf{u}_i)\cdot\mathbf{e}_2}{L_{ij}},\quad
\epsilon_{ij}^{(3)}=\frac{(\mathbf{u}_j-\mathbf{u}_i)\cdot\mathbf{e}_3}{L_{ij}}
$$

堆叠后得到：
$$
\epsilon = B u
$$

其中：

- $u \in \mathbb{R}^{3N}$
- $\epsilon \in \mathbb{R}^{3E}$
- $B \in \mathbb{R}^{3E\times 3N}$

这里每个符号的含义是：

- $N$：节点总数
- $E$：边总数
- $u$：把所有节点位移按节点顺序拼成一个长向量  
  $u=[u_{x1},u_{y1},u_{z1},\dots,u_{xN},u_{yN},u_{zN}]^T$
- $\epsilon$：把所有边的三个分量拼成一个长向量  
  $\epsilon=[\epsilon_{12}^{(1)},\epsilon_{12}^{(2)},\epsilon_{12}^{(3)},\dots]^T$
- $B$：把“节点位移”线性映射成“边上三方向梯度分量”的算子矩阵

本例：

- `N = 11`, `E = 10`
- 所以 $B$ 的尺寸是：
$$
B \in \mathbb{R}^{30\times 33}
$$

产物：

- 稀疏线性算子 `B`
- `edge_meta(node_i,node_j,length)`

### 2.3 Step C：位移转应变（原始）

将 `joined` 中位移拉平成向量 $u_{raw}$：
$$
u_{raw}=[u_{x1},u_{y1},u_{z1},\dots,u_{xN},u_{yN},u_{zN}]^T
$$

计算：
$$
\epsilon_{raw}=B\,u_{raw}
$$

本例统计（`Mode1`）：

- `max_abs_strain_raw = 0.142388`
- `max_stretch_raw = 0.0`
- `max_in_plane_bending_raw = 0.0`
- `max_out_plane_bending_raw = 0.142388`

说明此例应变主要集中在局部第三方向分量（由当前局部基定义）。

#### 可复核数值例子：边 (1,2)

本例边 `(1,2)`：

- $L_{12} \approx 0.10000000149$
- $\Delta \mathbf{u}=\mathbf{u}_2-\mathbf{u}_1=[0,0,-1.381695\times 10^{-3}]$
- 该边局部基接近：
$$
\mathbf{e}_1=[1,0,0],\ \mathbf{e}_2=[0,1,0],\ \mathbf{e}_3=[0,0,1]
$$

则：
$$
\epsilon_{12}^{(1)}=\frac{\Delta\mathbf{u}\cdot\mathbf{e}_1}{L_{12}}=0
$$
$$
\epsilon_{12}^{(2)}=\frac{\Delta\mathbf{u}\cdot\mathbf{e}_2}{L_{12}}=0
$$
$$
\epsilon_{12}^{(3)}=\frac{\Delta\mathbf{u}\cdot\mathbf{e}_3}{L_{12}}\approx -0.01381695
$$

与程序输出一致。

### 2.4 Step D：应变放大

对每个模态给定放大倍数 $s_m$（UI 中的 `scale`）：
$$
\epsilon_{scaled}^{(m)}=s_m\cdot\epsilon_{raw}^{(m)}
$$

本数据仅 `Mode1`，当 `scale=1.0` 时自然不变。

同一数据下的实测比例关系：

- `scale=1.0`：最大位移 `0.095245530`
- `scale=2.0`：最大位移 `0.190491060`
- `scale=5.0`：最大位移 `0.476227650`

### 2.5 Step E：最小二乘反算位移

反算目标：
$$
u_{scaled}=\arg\min_u ||Bu-\epsilon_{scaled}||_2
$$

为去除刚体平移不唯一性，代码附加 3 个锚定约束（首节点）：
$$
u_{x1}=0,\ u_{y1}=0,\ u_{z1}=0
$$

即求解增广系统：
$$
\begin{bmatrix}
B\\
A
\end{bmatrix}u=
\begin{bmatrix}
\epsilon_{scaled}\\
0
\end{bmatrix}
$$

其中 $A$ 只在首节点三个自由度上取 1。

本例（`Mode1`, `scale=1.0`）重构一致性：

- 相对应变残差
$$
\frac{||B u_{rec}-\epsilon_{raw}||_2}{||\epsilon_{raw}||_2}\approx 2.207\times 10^{-14}
$$

数值上接近机器精度。

产物：

- `scaled_df(node_id, ux, uy, uz, mode)`

### 2.6 Step F：模态加权组合

若有多模态，按 UI 中 `eta` 做线性组合：
$$
u_{comb}(i)=\sum_m \eta_m\,u_{scaled}^{(m)}(i)
$$

本例只有一个模态，且默认 $\eta_1=1$，故：
$$
u_{comb}=u_{scaled}
$$

并输出位移模长：
$$
disp\_mag(i)=||u_{comb}(i)||_2
$$

产物：

- `combined_df(node_id, ux, uy, uz, disp_mag)`

---

## 3. 每一步输入/产物总览（本例）

1. 输入文件
- `tbeamf.bdf`
- `tbeamf.f06`
- 参数：`scale=1.0`, `eta=1.0`

2. 中间产物
- `model.grids`: 11 节点
- `model.edges`: 10 边
- `disp_df`: 1 模态、11 条位移记录
- `B`: `30 x 33`
- `epsilon_raw`: 长度 30
- `epsilon_scaled`: 长度 30
- `u_scaled`: 长度 33（重排后 11x3）

3. 最终产物
- `summary_df`：每模态统计
- `scaled_df`：每模态放大后位移
- `edge_strain_df`：每条边应变分量
- `combined_df`：加权组合位移场

