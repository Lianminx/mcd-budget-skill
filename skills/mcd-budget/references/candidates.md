# 候选数据合同

候选由 Agent 根据本次门店菜单、套餐详情和券条件准备。输入采用 UTF-8 JSON，金额统一为元，营养统一为千卡和克；未知营养填 `null`。

```json
{
  "budget_yuan": "25.00",
  "require_side": false,
  "require_drink": true,
  "min_protein_g": 20,
  "store": {"storeCode":"真实门店编码","orderType":1,"beType":1},
  "offers": [
    {
      "id":"候选唯一标识",
      "name":"真实餐品名称及规格",
      "category":"main",
      "includes":["drink"],
      "price_yuan":"14.90",
      "price_source":"query-meals，本次查询时间",
      "energy_kcal":null,
      "protein_g":null,
      "coupon_ids":[],
      "quote_items":[{"productCode":"真实商品编码","quantity":1,"roundList":[]}]
    }
  ]
}
```

示意字段值不可直接用于真实调用；`roundList` 应填实际套餐子项。单品不需要 roundList。示例同时包含营养约束与未知营养，因此会被筛除；实际应填写已确认的总营养或移除不需要的约束。

`category` 为 `main`、`side`、`drink`。一个完整套餐放入 `main`，`includes` 注明已经含有的类别，防止额外再加同类餐品。`price_source` 必填。营养值覆盖整个候选，包括所有套餐子项。预算、`min_protein_g`、`max_energy_kcal` 是总量；两个营养约束可省略。`coupon_ids` 记录候选占用的实际券 ID，脚本排除重复占用，文件只保存在本地。

每类候选先筛选少量有价值项，总数不超过 60。脚本各选一个主食、零或一个小食、零或一个饮料，给出最多三个不同候选，不保证所有可行组合都出现在结果中。必须主食口味、过敏和禁忌条件由 Agent 在候选准备阶段处理。若报价失败或超预算，可移除该候选重新排序；不能说“没有任何方案”而只检查过三个候选。

```powershell
python skills/mcd-budget/scripts/plan.py examples/candidates.json
python skills/mcd-budget/scripts/quote.py local/candidates.json
```

`plan.py` 支持离线演示。`quote.py` 要求 `MCD_MCP_TOKEN`，将每个方案的 `quote_items` 合并，以单次 `calculate-price` 取得总价；不自行计算优惠、不创建订单。只有总应付、商品编码及数量检查通过且未超预算，才输出 `verified_price`。套餐子项没有在当前报价回执回显，输出会标明这一验证边界。
