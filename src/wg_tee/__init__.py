"""
wg_tee — 矩形波导 T 结工具包（AutoAnsys_Test）

模块分类
--------
- **paths**       仓库根路径、默认 config / output / results 路径解析。
- **geometry**    ModelDescribe §4：三臂与槽的轴对齐盒子（与 HFSS、preview 共用）。
- **params**      读取并校验 ``config/params.json`` → ``WGParams`` / ``SimulationParams``。
- **preview**     无 HFSS 的 3D 预览（trimesh + PyVista）；入口 ``wg-preview``。
- **hfss_session**  ``launch_hfss``：PyAEDT Modal HFSS 会话。
- **hfss_build**  HFSS 几何、PEC、端口、扫频；入口 ``wg-hfss``。
- **hfss_export** 求解并导出 S 参 CSV；入口 ``wg-solve-export``。
- **hfss_field_export** 顶面场 JPG（HFSS 场图或场计算器网格回退）；入口 ``wg-field-top``。
- **plot_s_params** 从 CSV 绘制 S11/S21/S31；入口 ``wg-plot-s``。
- **run_simulation** 一键建模→求解→CSV→曲线图；入口 ``wg-run-sim``。

详细说明见仓库根目录 ``README.md`` 与 ``ModelDescribe/ModelDescribe.md``。
"""
