# NastranIOConvert

`NastranIOConvert` 是一个用于模态位移后处理的小工具。它按以下链路计算大变形场：

`u -> epsilon (= B u) -> epsilon_scaled -> u_scaled (least squares)`

其中 `B` 由结构边局部坐标构建，`u_scaled` 通过最小二乘反算，最终再按 `eta` 做模态组合。

在线 Demo：  
[NastranIOConvert Streamlit App](https://nastranioconvert-kxr5eivbce3fzvbboie7g4.streamlit.app/)

## 1. 概览

项目用途：

- 读取 BDF（节点 + 结构边）
- 读取位移模态（CSV/F06）
- 在应变空间按输入放大倍数 `scale` 缩放
- 反算位移得到放大后的模态位移场
- 按权重 `eta` 组合多模态并导出

---

## 2. How It Works

### 2.1 输入符号

- 节点集合 `N`，节点坐标 `x_i = [x_i, y_i, z_i]^T`
- 结构边集合 `E`，边 `(i,j) ∈ E`
- 模态位移 `u_i^(m) = [ux, uy, uz]^T`
- 应变放大倍数 `scale_m`
- 模态权重 `eta_m`

### 2.2 构造应变算子 `B`

对每条边 `(i,j)`：

1. 计算边方向局部基

```math
e_1 = \frac{x_j-x_i}{\|x_j-x_i\|},\quad e_2,e_3 \perp e_1
```

2. 以 `e1/e2/e3` 三个方向分别形成一条线性约束，形如

```math
\epsilon_k = \frac{(u_j-u_i)\cdot e_k}{L_{ij}},\quad k\in\{1,2,3\}
```

把所有边的三条约束堆叠后得到

```math
\epsilon = B u
```

说明：当前实现对应三个局部方向分量（`stretch`, `in_plane_bending`, `out_plane_bending`），没有单独求解扭转自由度。

### 2.3 应变放大

每个模态 `m`：

```math
\epsilon^{(m)} = B u^{(m)}
```

```math
\epsilon_{scaled}^{(m)} = scale_m \cdot \epsilon^{(m)}
```

### 2.4 反算位移（最小二乘）

反算目标：

```math
u_{scaled}^{(m)} = \arg\min_u \|B u - \epsilon_{scaled}^{(m)}\|_2
```

实现中附加了 3 个锚定约束（首节点 `ux/uy/uz = 0`）以去除刚体平移不唯一性。

### 2.5 多模态组合

```math
u_i^{comb} = \sum_m \eta_m\,u_{i,scaled}^{(m)}
```

并计算

```math
disp\_mag = \|u_i^{comb}\|_2
```

---

## 3. 使用方法

### 3.1 安装

```bash
uv sync
```

### 3.2 运行

```bash
uv run streamlit run modal_strain_scaler_app.py
```

在线体验：  
[NastranIOConvert Streamlit App](https://nastranioconvert-kxr5eivbce3fzvbboie7g4.streamlit.app/)

可选：

```bash
uv run streamlit run main.py
```

### 3.3 页面输入

1. BDF（上传或粘贴）
2. 位移文件（CSV/F06/TXT）
3. `scale`（应变放大倍数）

`scale` 支持三种写法：

- 单值：`2.0`（所有模态同一倍数）
- 顺序：`1.0,0.8,1.2`（按模态顺序）
- 映射：`Mode1=2.0,Mode2=1.5`

4. `eta`（模态权重，可选）

`eta` 支持：顺序或映射两种写法；为空时默认每阶 `1.0`。

### 3.4 输入文件格式

CSV 最少列：

- `node_id`（或 `nid/grid/id`）
- `ux, uy, uz`（或 `t1, t2, t3`）
- `mode` 可选（缺省为 `Mode1`）

F06：当前解析的是位移向量表中的 `G` 点平移分量。

### 3.5 输出

- `summary.csv`：每模态统计（`input_scale`, `max_abs_strain_raw`, `max_disp_raw`, `max_disp_scaled` 等）
- `combined_deformed.csv`：按 `eta` 组合后的节点位移
- `combined_deformed.dat`：文本格式位移
- `mode_deformed_outputs.zip`：每个模态的反算后位移

---

## 4. Notes

- 若 BDF 没有 `CBAR`，程序会用节点 `k` 近邻（默认 `k=2`）自动补边。
- 若某些节点在 BDF 与位移文件中无法匹配，这些节点不会参与该模态计算。
- 出现 `1e-16` 量级的 `ux/uy` 通常是浮点残差，可视为 0。
