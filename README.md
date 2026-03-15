# NastranIOConvert

`NastranIOConvert` 是一个面向结构模态后处理的小工具：
给定结构模型（BDF）和模态位移（CSV/F06），在应变上限约束下自动计算每个模态的建议放大倍率，并生成加权组合变形场与可视化结果。

## 1. 首页（Overview）

这个工具解决的是一个很常见的问题：
原始模态位移幅值通常很小，直接看不直观；但盲目放大又可能超过可接受应变。

本项目通过“应变约束 + 自动缩放”的方式，让你可以：

- 从 BDF 中读取节点与结构连边（CBAR）
- 从 CSV/F06 中读取多模态位移
- 按允许应变 `epsilon_allow` 自动估算每个模态放大系数
- 按权重 `eta` 叠加各模态，得到组合位移场
- 在 Streamlit 页面中完成 3D 预览、统计与结果导出

---

## 2. How It Works（核心算法与步骤）

这一部分是项目核心：把位移场映射到结构边的轴向应变，并反推安全放大倍率。

### 2.1 输入与符号定义

设：

- 节点集合为 $\mathcal{N}$，节点 $i$ 的原始坐标为 $\mathbf{x}_i=[x_i,y_i,z_i]^T$
- 结构边集合为 $\mathcal{E}$，边 $(i,j)\in\mathcal{E}$
- 第 $m$ 个模态在节点 $i$ 的位移为 $\mathbf{u}_i^{(m)}=[u_{x},u_{y},u_{z}]^T$
- 用户给定允许最大应变 $\varepsilon_{allow}>0$
- 模态权重为 $\eta_m$

边长和单位方向向量：

$$
L_{ij}=\|\mathbf{x}_j-\mathbf{x}_i\|_2,
\qquad
\mathbf{n}_{ij}=\frac{\mathbf{x}_j-\mathbf{x}_i}{L_{ij}}
$$

### 2.2 单模态轴向应变估计

对每个模态 $m$、每条边 $(i,j)$：

1. 计算相对位移
$$
\Delta\mathbf{u}_{ij}^{(m)}=\mathbf{u}_j^{(m)}-\mathbf{u}_i^{(m)}
$$

2. 投影到边方向并除以边长，得到轴向应变近似
$$
\varepsilon_{ij}^{(m)} \approx \frac{\Delta\mathbf{u}_{ij}^{(m)}\cdot\mathbf{n}_{ij}}{L_{ij}}
$$

这是小变形线性近似下沿杆轴方向的应变估计，适合快速评估和放大建议。

### 2.3 模态放大系数求解

对每个模态，先取最大绝对应变：
$$
\varepsilon_{max}^{(m)}=\max_{(i,j)\in\mathcal{E}}\left|\varepsilon_{ij}^{(m)}\right|
$$

建议放大系数：
$$
\alpha_m=
\begin{cases}
\dfrac{\varepsilon_{allow}}{\varepsilon_{max}^{(m)}}, & \varepsilon_{max}^{(m)}>0 \\
1, & \varepsilon_{max}^{(m)}=0
\end{cases}
$$

缩放后的模态位移：
$$
\tilde{\mathbf{u}}_i^{(m)}=\alpha_m\,\mathbf{u}_i^{(m)}
$$

### 2.4 多模态加权组合

最终组合位移场：
$$
\mathbf{u}_i^{comb}=\sum_m \eta_m\,\tilde{\mathbf{u}}_i^{(m)}
$$

组合位移幅值：
$$
\|\mathbf{u}_i^{comb}\|_2=\sqrt{u_{x,i}^2+u_{y,i}^2+u_{z,i}^2}
$$

该量用于着色显示和导出结果中的 `disp_mag`。

### 2.5 关键实现细节

- 若同一模态下 `(mode, node_id)` 出现重复位移记录，先做均值聚合。
- 若 BDF 中无 CBAR，程序会基于节点坐标构建 k 近邻补边（默认 `k=2`）用于应变估计。
- F06 与 CSV 会自动识别；CSV 支持 `node_id/nid/grid/id` 和 `ux,uy,uz` 同义列。

### 2.6 算法流程（可对应代码）

1. 解析 BDF，得到 `grids` 与 `edges`。
2. 解析位移文件，得到每个模态的 `(node_id, ux, uy, uz)`。
3. 对每个模态：
   1) 对重复节点位移聚合；
   2) 逐边计算 $\varepsilon_{ij}^{(m)}$；
   3) 求 $\alpha_m$ 并缩放该模态位移；
   4) 记录统计量（最大应变、最大位移、节点数等）。
4. 用权重 $\eta_m$ 对缩放后模态叠加，得到组合场。
5. 输出 `summary`、`combined`、`per-mode zip` 并绘图。

---

## 3. Usage

### 3.1 Installation（安装）

推荐使用 `uv`：

```bash
uv sync
```

如果你只想快速安装运行依赖，也可：

```bash
uv pip install -e .
```

### 3.2 Run（启动）

```bash
uv run streamlit run modal_strain_scaler_app.py
```

可选入口：

```bash
uv run streamlit run main.py
```

### 3.3 使用步骤

1. 上传或粘贴 BDF（至少含 GRID；有 CBAR 更好）。
2. 上传或粘贴位移文件（CSV/F06）。
3. 设置 `epsilon_allow`。
4. 可选输入模态权重 `eta`：
   - 按顺序：`1.0,0.8,0.3`
   - 按名称：`Mode1=1.0,Mode2=0.6`
5. 查看 summary、应变分布图、3D 变形图。
6. 下载结果：`summary.csv`、`combined_deformed.csv/.dat`、各模态 ZIP。

### 3.4 输入输出约定（简版）

CSV 最少需要列：

- `node_id`（或 `nid/grid/id`）
- `ux, uy, uz`（或 `t1, t2, t3`）
- `mode` 可选（默认 `Mode1`）

输出文件：

- `summary.csv`：每个模态的应变与缩放统计
- `combined_deformed.csv`：加权组合位移场
- `combined_deformed.dat`：文本格式位移导出
- `mode_deformed_outputs.zip`：逐模态缩放结果
