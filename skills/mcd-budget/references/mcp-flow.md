# 实时 MCP 合同

来源：[麦当劳 MCP 使用指南](https://github.com/M-China/mcd-mcp-server)，以及 2026-10-10 对 `https://mcp.mcd.cn` 的 `tools/list` 实测。传输为 Streamable HTTP，认证头为 `Authorization: Bearer TOKEN`。

## 到店自取

| 工具 | 输入及用途 |
|---|---|
| `query-nearby-stores` | `{"city":"用户给出的城市","keyword":"用户给出的公共地标","searchType":2,"beType":1}`；结果让用户选店 |
| `query-meals` | `{"storeCode":"实际门店编码","orderType":1,"beType":1}`；获取当前可售餐品与价格 |
| `query-store-coupons` | 同上；当前账户在该门店可用的券，返回数据包含个人权益，勿公开原始数据 |
| `query-meal-detail` | 上述门店参数加 `code`；查看套餐默认组成、round、商品可选项 |
| `list-nutrition-foods` | `{}`；返回的业务 `data` 可能是 TOON 风格表格字符串 |
| `calculate-price` | 门店参数加 `items`；每项至少 `productCode`、`quantity`，券需要实际 `couponId`、`couponCode`，套餐需要实际 `roundList` |

到店自取不传 `beCode`。预约、得来速、外送和团餐有不同参数要求，不能复用本版参数。

单品价格核验示意（编码全部从工具结果取得）：

```json
{
  "storeCode": "实际门店编码",
  "orderType": 1,
  "beType": 1,
  "items": [{"productCode": "实际商品编码", "quantity": 1}]
}
```

`calculate-price` 的价格字段单位为分。选择官方应付总额，除以 100 得到元；不能直接使用原价、优惠金额或商品合计代替应付总额。返回的金额字段名以实际响应为准，遇到陌生结构不要猜测。

套餐 `roundList` 必须依据详情的默认或用户选定的组成生成。餐品特制涉及 selectedKey/unselectedKey 配对，本版默认不主动改特制。出现需要特制的要求时先读取当前工具完整描述。

## 本地 CLI

Python 3.10+，仅用标准库。在环境中配置 `MCD_MCP_TOKEN` 后：

```powershell
python skills/mcd-budget/scripts/mcp_client.py tools
python skills/mcd-budget/scripts/mcp_client.py call query-nearby-stores --input local/store-search.json
python skills/mcd-budget/scripts/mcp_client.py call list-nutrition-foods
python skills/mcd-budget/scripts/mcp_client.py call calculate-price --input local/quote.json
```

`--input` 读取 UTF-8 JSON 对象，避免复杂命令行转义。不要把 Key 放入文件。只读工具允许列表固定，不提供任意工具调用入口。CLI 输出完整业务响应用于本地处理；账户券、门店报价和定位输入保存在被忽略的 `local/`，不能把它们原样放入公开材料。

CLI 初始化、发送 initialized 通知，随后查询工具或调用允许的只读工具；支持 JSON 和事件流响应、会话头、业务错误处理。发生网络或认证错误时终止，不重试写操作，也不输出认证头。
