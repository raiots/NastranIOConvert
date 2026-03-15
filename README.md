# NastranIOConvert

用于把 BDF + 模态位移数据转换为应变约束下的放大位移场，并通过 Streamlit 进行可视化与导出。

## 运行

```bash
uv run streamlit run modal_strain_scaler_app.py
```

## 项目结构

- `modal_strain_scaler_app.py`：兼容入口（保留旧启动方式）
- `main.py`：统一入口
- `nastranioconvert/models.py`：数据模型
- `nastranioconvert/parsers/`：BDF/F06/CSV 解析
- `nastranioconvert/services/`：应变计算与组合逻辑
- `nastranioconvert/visualization/`：3D 图形构建
- `nastranioconvert/utils/`：文本与导出工具
- `nastranioconvert/ui/`：Streamlit 页面
