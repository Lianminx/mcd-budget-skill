# 麦当劳 MCP 集成

## 服务与工具

实际接入 `https://mcp.mcd.cn`，采用 Streamable HTTP 和 Bearer Token。Token 来自客户端私有凭证设置或本地环境变量 `MCD_MCP_TOKEN`，不在源代码、配置样例或日志中保存。

| 工具 | 实际业务用途 |
|---|---|
| `query-nearby-stores` | 根据用户提供城市和公共地标定位门店 |
| `query-meals` | 取得本门店当前商品编码、价格、条件和类别 |
| `query-store-coupons` | 获取用户在本门店可用的权益，避免推荐不可用的券 |
| `query-meal-detail` | 展开套餐 round 和真实子项，核对规格与数量 |
| `list-nutrition-foods` | 严格匹配餐品，计算已知热量与蛋白质 |
| `calculate-price` | 以真实编码、套餐组成和券条件核验总应付金额 |

本地客户端另允许 `now-time-info`，用于需要服务端时间的场景；本次预算链路没有调用它。只读允许列表没有领券、积分扣减、抽奖、下单或取消订单工具。

## 调用流程

用户预算与偏好 → 选定到店自取门店 → 查询菜单和门店可用券 → 查询套餐详情与营养 → 构建候选 → 本地排序 → 逐个 `calculate-price` → 核对商品和预算 → 展示方案。

`plan.py` 只排序输入候选，不宣称菜单估价是最终成交价格。`quote.py` 仅提交选中候选的价格计算参数，通过应付 `data.price`（分）与 `data.productList` 商品数量校验后再标记 `verified_price`。

实测发现菜单 `currentPrice` 是带小数的元金额，而 `calculate-price` 价格字段是整数分，二者必须分别处理。菜单购卡价格和会员价格存在额外条件；本版不购买卡，也不把这些价格当作无条件售价。

实测套餐 round 可能有多个 `isDefault=1`，但只有一个 `quantity>0` 的默认选中项。准备默认组成时优先检查实际 quantity；用户指定替换时用对应 choices 编码与详情中的差价，最后重新核价。营养严格依据真正选择的子项计算。

## 业务价值

预算从“感觉够不够”转为实时总价比较，套餐从营销名称转为实际组成。用户可以比较不同方案，而不必在菜单、券和营养表之间反复切换。

本次真实核验的三种方案分别为 14.90 元、14.90 元和 22.90 元，详见 [VALIDATION.md](VALIDATION.md)。这些是历史结果，不承诺当前价格或全菜单最低价。个人可用券分支成功查询但返回空列表，尚未取得有券账户的成功核验样本。

报价响应未回显套餐子项和指定券明细，因此无法仅凭该响应证明内部选项或券使用完全一致；代码与文档保留这个限制。没有调用订单创建，不声称完成购买或取餐。

## 来源

- [麦当劳 MCP 官方接入指南](https://github.com/M-China/mcd-mcp-server)
- 2026-10-10 实测 `tools/list` 及上表六种工具，脱敏证据见 [VALIDATION.md](VALIDATION.md)
- [官方参赛规则](https://github.com/M-China-Official/mcd-developer-innovation-challenge/blob/main/activityGuidelines.md)
