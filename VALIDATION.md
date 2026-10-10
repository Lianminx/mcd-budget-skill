# 首轮验证记录

日期：2026-10-10，北京时间。来源为真实麦当劳 MCP 调用、本地脚本运行输出及官方声明文件。未创建订单、领取券、扣积分、购买会员卡或使用 WorkBuddy。

## 环境和输入

- 服务：`https://mcp.mcd.cn`，Streamable HTTP。
- 客户端：项目 `mcp_client.py`，Python 标准库。
- 用户给出的公共地点：北京沙河万达。
- 门店：麦当劳北京乐业路（昌平万达）餐厅，`storeCode=1950828`，搜索响应显示当前营业。
- 场景：即时到店自取，`orderType=1, beType=1`。
- 预算：25 元，无必须饮料或小食约束。

## 真实调用

| 环节 | 结果 | 证据范围 |
|---|---|---|
| 初始化与工具发现 | 成功，发现 35 个工具 | 证明连接和工具清单可用 |
| `query-nearby-stores` | 成功，查询地标附近门店 | 定位来自用户提供的公共地点 |
| `query-meals` | 成功，取得门店商品编码和 currentPrice | 菜单含购卡价格，本次不采用购卡候选 |
| `query-store-coupons` | 成功，空列表 | 仅说明本次账户、门店和场景下未返回可用券 |
| `query-meal-detail` | 成功，取得套餐 rounds 和 choices | 发现部分 round 多个 isDefault=1，不能全部作为选中项 |
| `list-nutrition-foods` | 成功，160 条营养记录 | 按实际子项品名与规格匹配；未知不补零 |
| `calculate-price` | 三方案成功 | 顶层商品编码及数量一致，总价在预算内 |

三种候选通过 `quote.py` 查询；只发布脱敏后的摘要，原始账户数据留在 Git 忽略的 `local/`。

| 方案 | 商品及实际选择的子项 | 返回总应付（分） | 展示金额 | 营养依据 |
|---|---|---:|---:|---|
| 省钱 | 人气经典随心配：双层吉士汉堡、无糖可口可乐中杯 | 1490 | 14.90 元 | 429 + 0 千卡，27 + 0 克蛋白质 |
| 蛋白质优先 | 人气经典随心配：双层吉士汉堡、小杯玉米杯 | 1490 | 14.90 元 | 429 + 53 千卡，27 + 2 克蛋白质 |
| 组合丰富 | 大堡口福三件套：Hold不住鸡排堡（椒盐风味）、中薯条、无糖可口可乐中杯 | 2290 | 22.90 元 | 主食未严格匹配到营养数据，整餐总营养保留未知 |

最终报价时间为 10:54:53—10:54:54。候选营养是根据接口数据相加，不是模型估计。

## 最小本地检查

运行 `python checks/check_budget.py`，10 项检查通过：小数金额与非法值、套餐不重复加餐、营养未知时约束排除、同券不重复占用、重复候选 ID、估价超预算但保留核价机会、报价临界预算、报价商品数量匹配、SSE 请求匹配与协议错误、业务失败与写工具阻断。

`skill-creator/scripts/quick_validate.py skills/mcd-budget` 返回 `Skill is valid!`。离线虚构样例产生三个不同候选，状态均为 `needs_live_quote`。官方 `CONTEST_DECLARATION.md` 直接下载，内容未修改。

## 尚未证明的事项

- 本次账户无可用券，未取得指定优惠券被实际采用的成功样本。
- 报价返回顶层套餐商品和数量，没有回显套餐内部选项；总价核验不能独立证明内部选项回显一致。
- 第三种方案缺失完整营养数据，不能声称满足指定热量或蛋白质目标。
- 未覆盖全菜单；候选集内排序不能证明全店最省钱或营养最优。
- 尚未完成目标 Agent 新会话中的自动路由验收。
- 尚未发布公开 GitHub 仓库和提交报名 Issue，不能声称已经报名成功。

## 来源文件

- 本项目 `skills/mcd-budget/scripts/mcp_client.py`、`plan.py`、`quote.py` 和 `checks/check_budget.py`
- 2026-10-10 本地查询响应：门店、菜单、门店券、营养、套餐详情和报价；含账户数据的原件不公开
- [官方 MCP README](https://github.com/M-China/mcd-mcp-server/blob/main/README.md)
- [官方活动规则](https://github.com/M-China-Official/mcd-developer-innovation-challenge/blob/main/activityGuidelines.md)
- [官方参赛声明](https://github.com/M-China-Official/mcd-developer-innovation-challenge/blob/main/CONTEST_DECLARATION.md)
