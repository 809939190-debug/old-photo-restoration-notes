# 基准实验

用 13 张公有领域老照片 + 合成退化，比较 5 种修复方法。

## 数据从哪来

Wikimedia Commons 的 PD/CC0 人像与合影，脚本按分类抓取（注意限流，实际是慢慢攒的）。
**仓库不包含图片**，需要自己跑 `collect.py` 抓取。

## 流程

```bash
python benchmark/make_inputs.py      # 干净图 → 半分辨率 → 合成退化
python benchmark/degrade_levels.py   # 生成 L1~L4 四档退化
python benchmark/classical_levels.py # 传统方法基线（本地，免费）
# 生成模型方法需要调 API，见 src/seedream.py
python benchmark/metrics.py          # PSNR / SSIM / ArcFace / 损伤残留
python benchmark/make_grid_v2.py     # 出对比图
```

## 指标说明

| 指标 | 实现 | 说明 |
|---|---|---|
| PSNR / SSIM | 纯 numpy/cv2 | 与真值逐像素比较 |
| 人脸相似度 | SCRFD(det_500m) + ArcFace(w600k) | 余弦相似度，1.0 = 同一人 |
| 损伤区残留 | 蒙版内平均绝对误差 | 只统计被破坏区域 |

模型从 insightface 的 `buffalo_sc` 包获取（14MB）。

## 已知问题

- 合成退化无法复现真实霉斑的纹理
- 13 张样本量偏小
- 生成模型只跑了单种子
