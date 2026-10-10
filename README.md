# 麦麦预算搭配师

**给一个预算和口味，拿到有门店、有组成、经实时价格核验的麦当劳搭配方案。**

面向想在预算内选餐、比较搭配的用户。用自然语言提出需求，由支持 Skill 的 Agent 联合麦当劳 MCP 完成门店查询、餐品筛选、营养匹配与报价核验。Python 脚本处理候选组合和金额计算，不需要 WorkBuddy。

> 示例：“北京沙河万达附近，25 元以内，想吃汉堡。帮我比较省钱、蛋白质优先和主食小食饮料都有的方案。”

本项目为独立开发的参赛作品，非麦当劳官方产品。

项目仓库：[Lianminx/mcd-budget-skill](https://github.com/Lianminx/mcd-budget-skill) · 报名申请：[官方 Issue #205](https://github.com/M-China/mcd-developer-innovation-challenge/issues/205)。报名回执记录见 [SUBMISSION.md](SUBMISSION.md)。

## 一次真实查询

2026-10-10 10:51（北京时间），北京乐业路（昌平万达）餐厅，到店自取，预算 25 元。以下总应付由 `calculate-price` 返回，营养来自当次 `list-nutrition-foods` 查询。

| 搭配 | 核验应付 | 预算余量 | 热量 | 蛋白质 |
|---|---:|---:|---:|---:|
| 双层吉士汉堡 + 无糖可口可乐中杯 | ¥14.90 | ¥10.10 | 429 千卡 | 27 克 |
| 双层吉士汉堡 + 小杯玉米杯 | ¥14.90 | ¥10.10 | 482 千卡 | 29 克 |
| Hold不住鸡排堡（椒盐风味）+ 中薯条 + 无糖可口可乐中杯 | ¥22.90 | ¥2.10 | 未取得完整数据 | 未取得完整数据 |

这是历史实测示例，不能作为当前售价。第二种没有饮料；若用户要求必须有饮料，会被筛除。营养未知不会当作零，也不会用相似名字餐品的数据替代。报价回执回显套餐顶层商品及数量，未回显内部选项，验证边界见 [实测记录](VALIDATION.md)。

## 安装

1. 取得本项目文件，使用 Python 3.10 或更高版本。脚本仅用 Python 标准库。
2. 将 `skills/mcd-budget` 文件夹复制到目标 Agent 的 Skill 目录。例如 Codex 用户目录 `~/.codex/skills/mcd-budget`。其他客户端使用其支持的 Skill 导入方式。
3. 在目标 MCP 客户端添加麦当劳 MCP：`https://mcp.mcd.cn`，Streamable HTTP，使用自己的 Token 认证。[官方接入指南](https://github.com/M-China/mcd-mcp-server)
4. 参考 [mcp-config.example.json](mcp-config.example.json) 配置。该文件仅含环境变量占位符；客户端若不支持变量展开，应在其私有凭证设置中填入 Token。不要把替换后的配置提交到仓库。
5. 开启能读取 Skill 的新会话，输入 `$mcd-budget` 或上述自然语言需求。客户端的发现、加载和工具挂载是否成功须在该会话确认，复制文件不等于已生效。

Skill 正文位于 [SKILL.md](skills/mcd-budget/SKILL.md)。第一版支持单人即时到店自取；不会自动领券、下单、抽奖、兑换积分或购卡。

## 不挂载 MCP 也能本地调用

在系统或当前终端环境中设置 `MCD_MCP_TOKEN`，用自己的凭证，不要写入代码。Windows 可用下面的隐藏输入配置当前终端：

```powershell
$mcdSecret = Read-Host '输入麦当劳 MCP Token' -AsSecureString
$env:MCD_MCP_TOKEN = [System.Net.NetworkCredential]::new('', $mcdSecret).Password
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
python skills/mcd-budget/scripts/mcp_client.py tools
```

在 `local/` 中准备 UTF-8 JSON 参数文件（目录被 Git 忽略），用 [MCP 流程](skills/mcd-budget/references/mcp-flow.md) 查询门店、菜单、券与套餐组成。Agent 根据这些真实响应准备候选，格式见 [候选数据合同](skills/mcd-budget/references/candidates.md)。

```powershell
# 离线演示：完全虚构的餐品和价格，不调用 MCP
python skills/mcd-budget/scripts/plan.py examples/candidates.json

# 真实核价：输入必须来自本次门店菜单和套餐详情
python skills/mcd-budget/scripts/quote.py local/candidates.json

# 完成后清除当前终端凭证
Remove-Item Env:MCD_MCP_TOKEN
```

`verified_price` 表示总价与顶层商品数量匹配且在预算内；`over_budget` 和 `quote_failed` 不能当成可行推荐。菜单估价不替代报价，示例价格不用于真实调用。

## 组合方法

```mermaid
flowchart LR
  A[预算与偏好] --> B[选门店]
  B --> C[实时菜单与可用券]
  C --> D[套餐组成与营养匹配]
  D --> E[候选组合与排序]
  E --> F[实时总价核验]
  F --> G[预算内方案与限制]
```

脚本枚举输入候选集里的一个主食或套餐、可选小食及饮料，比较省钱、已知蛋白质和组合丰富程度。候选集由 Agent 准备，不保证全菜单最优。优惠券适用条件和套餐内部选择由实时工具结果确定，报价后超预算再调整。

## 验证与来源

```powershell
python checks/check_budget.py
```

验证包括小数金额、缺失营养、套餐不重复加餐、同券不重复占用、超预算以及报价商品不一致等边界；真实链路记录见 [VALIDATION.md](VALIDATION.md)，工具说明见 [MCP_INTEGRATION.md](MCP_INTEGRATION.md)。

项目规则来源文件：[官方 README](https://github.com/M-China-Official/mcd-developer-innovation-challenge/blob/main/README.md)、[activityGuidelines.md](https://github.com/M-China-Official/mcd-developer-innovation-challenge/blob/main/activityGuidelines.md)、[CONTEST_DECLARATION.md](https://github.com/M-China-Official/mcd-developer-innovation-challenge/blob/main/CONTEST_DECLARATION.md)。MCP 来源：[服务仓库 README](https://github.com/M-China/mcd-mcp-server/blob/main/README.md)及 2026-10-10 的真实工具清单、门店、菜单、营养与报价响应。

营养输出仅供一般参考；餐品、售价、供应和权益以麦当劳官方实时结果为准。所有个人 Token、账户权益和原始本地响应不进入公开仓库。
