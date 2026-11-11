# 老照片修复流水线 · Old Photo Restoration Pipeline

用「PDF 拆图 → 超分放大 → 视觉大模型修复 → 调色柔化 → 出对比图」重做一张扫描件里的多张家庭老照片。

> 在 2026 年跑通了 11 张 1990 年代前的纸质老照片（含单人像、合影、风景合影），
> 从一张 A4 扫描 PDF 里拆出、修复、上色，全流程约 20 分钟。
> **仓库只包含代码与文档，不含任何真实家庭照片。**

## 为什么不用传统方案

| 方案 | 结果 |
| --- | --- |
| Real-ESRGAN / GFPGAN | 只能提清晰度，**大面积霉斑、水渍、划痕原样保留** |
| DiffBIR v2.1（扩散模型） | 同样只能强化细节，清不掉污渍；CPU 上 4 小时/张 |
| LaMa 抠图修复 | 需要人工精确蒙版，自动蒙版会把人物一起抹掉 |
| **Seedream 图生图** | **清污效果最好**，代价是会把脸"重画"，所以需要下面两条约束 |

结论：**清污交给生成模型，保真交给「先放大 + 强约束提示词 + 柔化」**。

## 流水线

```
扫描 PDF
  │  render_pdf.py        300dpi 光栅化
  ▼
整页图
  │  extract_crops.py     用截图模板匹配定位每张照片，还原裁切框
  ▼
单张原图 (crop_user/)
  │  upscale.py           Lanczos ×2.5 + 轻微锐化
  ▼
放大图
  │  seedream.py restore  PRO 模型图生图，提示词锁死"保留五官、不得美化"
  ▼
修复图（黑白、无花边）
  │  seedream.py color    可选：克制的年代上色
  ▼
彩色图
  │  finish.py soften     高斯柔化 + 颗粒 + 褪色；finish.py mute 降饱和
  ▼
成品 + 对比图
```

## 快速开始

```bash
pip install -r requirements.txt
export ARK_API_KEY=你的火山方舟密钥      # Windows: set ARK_API_KEY=...

# 1. PDF 拆页
python src/render_pdf.py scan.pdf -o work/page.png --dpi 300

# 2. 自动定位每张照片（需要把每张照片的截图放 screens/ 里）
python src/extract_crops.py work/page.png --screens screens/ -o crop_user/

# 3. 放大
python src/upscale.py crop_user/ -o up_all/ --scale 2.5

# 4. 修复（黑白）
python src/seedream.py restore up_all/ -o restored/ --model pro

# 5. 上色（可选）
python src/seedream.py color restored/ -o colored/

# 6. 柔化 / 降饱和 / 出对比图
python src/finish.py soften restored/ -o final_bw/
python src/finish.py mute colored/ final_bw/ -o final_color/
python src/finish.py sheet crop_user/ final_bw/ final_color/ -o work/compare.png
```

## 关键经验（踩过的坑）

1. **提示词必须点名"嘴型、脸型、眉眼不得改变"**，只写"保留人物特征"模型会自由发挥。
2. **先放大再送模型**，比直接送小图保真度高得多——小图会触发模型"重新想象"。
3. **PRO 比 flash 保真**：同样提示词下 flash 会把合影里的人修成"同一张脸"。
4. **柔化是必需品**：模型输出偏锐，直接用像 CG 图；1.1~1.4px 高斯 + 颗粒后才有胶片感。
5. **上色后要降饱和**（~72%）并混入 15~20% 黑白，否则像油画。
6. **不要指望自动去花边**：波浪边裁切必切画面，改成让模型重绘"无边框版本"。
7. CPU 只能跑传统模型；扩散模型在 32GB 内存机器上需要分块推理，4 小时/张，不划算。

## 目录

```
src/
  render_pdf.py     PDF → 300dpi 页面图
  extract_crops.py  截图模板匹配 → 裁切框
  upscale.py        超分放大
  seedream.py       火山方舟 Seedream 客户端（restore / color 子命令）
  finish.py         柔化、降饱和、对比图
docs/
  pipeline.md       各步骤参数与调参记录
```

## 许可

MIT。代码可自由使用；**请勿把他人照片、密钥提交进仓库**。
