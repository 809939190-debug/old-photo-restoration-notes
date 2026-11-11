# 复现指南

两种方式：把下面对话指令粘给任意 AI 编码助手，或者直接用命令行。

> 需要：一个火山方舟 API Key（[控制台](https://console.volcengine.com/ark) 申请，需开通 **Seedream 5.0 Pro**）。
> 成本参考：单张 2~3 元（含重试），11 张约 30 元以内。

---

## 方式一：把这段粘给 AI 助手

\`\`\`
帮我修一批老照片。素材是一张 A4 扫描 PDF，里面有多张纸质老照片。

流程按这个来，每步做完再进下一步：
1. 用 pypdfium2 把 PDF 按 300dpi 光栅化成 PNG
2. 定位每张照片的裁切框（有截图就用模板匹配，没给就自动检测暗色矩形），裁出来
3. 每张 Lanczos 放大 2.5 倍，轻微锐化
4. 调火山方舟 Seedream 5.0 Pro 图生图清污：
   - 接口 https://ark.cn-beijing.volces.com/api/v3/images/generations
   - 提示词必须点名"保留五官相貌、脸型、嘴型、眉眼，不得美化"
   - 输出 2K
5. 后处理：高斯柔化 1.1~1.4px + 胶片颗粒 + 色阶归一

硬约束（违反会翻车）：
- 必须先放大再送模型，不要直接送小图
- 每张照片只调用一次修复，不要重复修
- 上色可选，黑白更稳（多一道生成就多一次漂移）
- 提示词里都要写"不要添加原图没有的物品"

API key 我稍后给你，读环境变量 ARK_API_KEY。
先跑 1 张给我看效果，确认后再批量。
\`\`\`

---

## 方式二：命令行

\`\`\`bash
git clone https://github.com/809939190-debug/old-photo-restoration-notes
cd old-photo-restoration-notes
pip install -r requirements.txt

# Windows 用 set ARK_API_KEY=...
export ARK_API_KEY=你的密钥

python src/render_pdf.py scan.pdf -o work/page.png --dpi 300
python src/extract_crops.py work/page.png --screens screens/ -o crop_user/
python src/upscale.py crop_user/ -o up_all/ --scale 2.5
python src/seedream.py restore up_all/ -o restored/ --model pro
python src/finish.py soften restored/ -o final_bw/

# 可选：上色（多一道生成，漂移风险略高）
python src/seedream.py color restored/ -o colored/
\`\`\`

### 没有截图怎么办

\`extract_crops.py\` 需要 `screens/` 里放过每张照片的截图。
没有截图时可以手工裁切，把结果放进 `crop_user/`，后续步骤不变。

---

## 三个最容易翻车的点

### 1. 直接送小图

300px 宽的小图喂进去，模型会倾向"重新想象"这张脸——合影里五个人可能被修成同一张脸。

**必须先放大到 2000px 量级再送。**

### 2. 反复修

同一个模型连续修两次，第二遍五官开始漂移，第三遍就不是本人了。

**每张只修一次。** 不满意就换提示词重来，不要在同一张输出上叠加。

### 3. 提示词写得太泛

写"保留人物特征"没有用。必须点名部位：

\`\`\`
严格保留人物原有的五官相貌、脸型、嘴型与眉眼，
不得美化、不得改变长相，不要添加原图没有的物品或装饰。
\`\`\`

---

## 费用

| 项目 | 单价 | 说明 |
|---|---|---|
| Seedream 5.0 Pro 图生图 | 约 0.25 元/次 | 2K 输出 |
| 单张照片 | 2~3 元 | 含清污 + 去边框 + 可能的重试 |
| 11 张全套 | 30 元以内 | 黑白版；加上色再多 |

**建议先跑 1 张确认效果，再批量。**

---

## 注意

- **密钥**：只放环境变量，不要写进代码或提交到仓库
- **照片**：家庭照片不要推到公开仓库，`.gitignore` 已排除所有图片
- **模型会更新**：提示词是针对 Seedream 5.0 调的，换模型需要重新试
