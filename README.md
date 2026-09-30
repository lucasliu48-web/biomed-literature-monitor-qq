# 生物医药顶刊文献监控机器人

自动监控 PubMed 上国内外顶级生物医药期刊的最新文献，AI 智能汇总后通过 QQ 邮箱推送。

## 功能

- 监测 **35+ 本**国内外顶级生物医药期刊（CNS、医学顶刊、Nature/Cell 子刊、国内顶刊）
- 基于 **PubMed E-utilities API**（完全免费，无需 API Key）
- 自动过滤新闻、社论等非研究论文
- AI 智能汇总（豆包大模型，未配置 Key 时降级为规则摘要）
- QQ 邮箱推送 HTML 与纯文本简报（含 AI 汇总、文献列表、原文链接）
- 去重机制（基于 PMID）
- GitHub Actions 每日自动运行（北京时间早 8 点）

## 监测期刊列表

| 分组 | 期刊 |
|------|------|
| 综合顶刊 (CNS) | Nature, Science, Cell |
| 医学顶刊 | NEJM, Lancet, JAMA, BMJ |
| Nature 子刊 | Nature Medicine, Nature Biotechnology, Nature Genetics, Nature Biomedical Engineering, Nature Cell Biology, Nature Cancer, Nature Microbiology, Nature Immunology, Nature Neuroscience |
| Cell 子刊 | Cancer Cell, Immunity, Neuron, Cell Stem Cell, Molecular Cell, Cell Metabolism, Cell Host & Microbe |
| 其他重要期刊 | PNAS, Cell Research, Blood, Circulation, Genome Biology, Genome Research |
| 国内顶级期刊 | Science China Life Sciences, Journal of Molecular Cell Biology, Acta Pharmacologica Sinica, Chinese Medical Journal |

## 快速开始

### 本地运行

```bash
pip install requests
# 初始化（标记现有文献为已读，不推送）
python pubmed_monitor.py --init
# 运行一次
python pubmed_monitor.py --once
```

### 配置

编辑 `config.json`，或设置同名大写环境变量：
- `qq_email_sender` / `QQ_EMAIL_SENDER`：发件 QQ 邮箱
- `qq_email_auth_code` / `QQ_EMAIL_AUTH_CODE`：QQ 邮箱 SMTP 授权码（不要使用登录密码，也不要写入仓库）
- `email_recipient` / `EMAIL_RECIPIENT`：收件邮箱
- `ai_api_key`：火山引擎方舟 API Key（可选，不配置用规则摘要）
- `check_days`：监测最近几天的文献（默认 3 天）
- `journals`：监测的期刊列表（可自行增删）

### GitHub Actions 部署（推荐）

1. 在发件 QQ 邮箱的设置中开启 SMTP 服务并获取授权码
2. 在仓库 Settings → Secrets and variables → Actions 中添加：
   - `QQ_EMAIL_SENDER`：发件 QQ 邮箱地址
   - `QQ_EMAIL_AUTH_CODE`：QQ 邮箱 SMTP 授权码
   - `EMAIL_RECIPIENT`：收件邮箱地址
   - `AI_API_KEY`：火山引擎 API Key（可选）
3. 仓库已有 `seen_pmids.json` 去重记录；新部署且没有记录时，可先运行 `python pubmed_monitor.py --init`
4. 在 Actions 中手动运行一次工作流检查；之后每天北京时间早 8 点自动运行。只有发信成功才更新去重记录

### 中文解读补充邮件（手动触发）

每天早上的原始文献简报照常自动发送。中文翻译与解读由 Codex 根据 PubMed 摘要逐批生成，不调用付费模型 API。要发送新一批中文解读：

1. 将当天文献交给 Codex，生成 `analysis/YYYY-MM-DD.json`。每篇至少有 `title_zh`；有 PubMed 摘要时同时填写 `abstract_zh` 和 `analysis_zh`。未核对全文的结论要明确标注局限。
2. 将该 JSON 文件提交到仓库的 `analysis/` 文件夹。
3. 打开 Actions → **发送中文文献解读** → **Run workflow**。工作流会读取日期最新的解读文件，通过已有 QQ 邮箱 Secrets 发送一封补充邮件。

成功后日期写入 `analysis_sent.json`；再次运行同一日期会跳过。新文献的翻译与解读需要 Codex 再次处理，无法由现有 GitHub 定时任务自行生成。

## 文件结构

```
biomed_literature_monitor/
├── .github/workflows/monitor.yml  # GitHub Actions 定时任务
├── .github/workflows/analysis_digest.yml  # 中文解读手动发送
├── pubmed_monitor.py               # 主程序
├── email_delivery.py               # QQ 邮箱发送与简报格式
├── send_analysis_digest.py         # 中文解读补充邮件
├── analysis/                       # Codex 人工准备的中文解读
├── analysis_sent.json              # 已发送解读日期（工作流生成）
├── config.json                     # 配置文件（期刊列表、邮件、AI等）
├── requirements.txt                # Python 依赖
├── seen_pmids.json                 # 已推送文献记录（自动生成）
└── README.md                       # 本说明
```

## 推送效果

收件邮箱收到一封简报，包含日期、新文献数、摘要和按期刊分组的 PubMed 链接。无新文献时不发送邮件。
