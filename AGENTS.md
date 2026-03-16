# AGENTS.md

## 项目概览

这是一个基于 Python 3.11 的 Streamlit 应用，用于把 Nastran 模态位移场按如下链路做后处理：

`u -> epsilon (= B u) -> epsilon_scaled -> u_scaled`

主要能力：

- 解析 BDF 中的节点与结构边
- 解析 CSV/F06 位移结果
- 在应变空间放大模态
- 用最小二乘反算放大后的位移
- 在网页中可视化并导出结果

## 仓库结构

- `main.py`: 本地运行入口，只负责调用 Streamlit app
- `nastranioconvert/ui/`: Streamlit 页面、默认示例数据、调试面板
- `nastranioconvert/parsers/`: BDF、CSV、F06 和参数解析
- `nastranioconvert/services/`: 应变算子构建、应变估计、位移反算
- `nastranioconvert/visualization/`: Plotly 图形生成
- `nastranioconvert/utils/`: 文本与导出工具
- `data/`: 示例输入文件
- `docs/`: 补充说明文档

## 环境与命令

优先使用 `uv`。

安装依赖：

```bash
uv sync
```

运行应用：

```bash
uv run python main.py
```

或：

```bash
uv run streamlit run main.py
```

也可以直接运行项目脚本：

```bash
uv run nastranioconvert
```

如果沙箱环境下 `uv` 因缓存目录无权限失败，优先加上：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ...
```

## 开发约定

- 修改前先确认变更落点：解析逻辑放 `parsers/`，数值计算放 `services/`，UI 只负责组织输入输出与展示。
- 不要把业务计算直接塞进 `streamlit_app.py`；新增计算逻辑应优先放到独立模块。
- 解析器要继续兼容当前 README 中说明的输入格式和列名别名。
- 当前项目没有自动化测试目录；改动后至少做一次导入检查，必要时手动跑 Streamlit 页面验证主流程。
- 输出文件格式和列名应保持稳定，避免破坏 `summary.csv`、`combined_deformed.csv`、`combined_deformed.dat` 和 ZIP 导出。
- 这是数值处理项目，涉及矩阵维度、节点顺序、模态名映射时，优先显式处理，不要依赖隐式顺序假设。

## 推荐验证方式

轻量检查：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python -c "import nastranioconvert, main; print('ok')"
```

手动验证：

1. 启动 Streamlit
2. 使用 `data/` 下示例文件或默认示例数据
3. 检查 summary、3D 图和导出按钮是否正常

## 修改时的注意点

- `three_component` 与 `four_component` 两种模式共存，修改应变相关逻辑时必须同时检查两条路径。
- `solve_displacement_from_strain` 通过首节点锚定去除刚体平移，自由度约束相关改动需要评估是否影响现有结果。
- F06 解析依赖固定文本模式；若扩展格式，优先新增兼容逻辑，不要轻易破坏现有正则。
- 文档和代码中的中文面向最终用户，新增界面文案默认保持中文。
