"""Quote prepared candidates using the real store; never create an order."""
import argparse
from collections import Counter
from decimal import Decimal
import json
import os

from mcp_client import Client, MCPError, business_response
from plan import money, solve


def checked_quote(data, items, budget):
    cents = data.get("price")
    if isinstance(cents, bool) or not isinstance(cents, int) or cents < 0:
        raise MCPError("报价总应付字段未知，无法确认金额。")
    requested = Counter()
    for item in items:
        requested[item["productCode"]] += item["quantity"]
    actual = Counter()
    products = data.get("productList")
    if not isinstance(products, list) or not products:
        raise MCPError("报价未返回商品清单。")
    for product in products:
        quantity = product.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise MCPError("报价商品数量无效。")
        actual[product["productCode"]] += quantity
    if actual != requested:
        raise MCPError("报价商品或数量与候选不一致。")
    amount = Decimal(cents) / 100
    return {"status": "verified_price" if amount <= budget else "over_budget",
            "payable_yuan": f"{amount:.2f}", "remaining_yuan": f"{budget - amount:.2f}"}


def quote_plans(document, client):
    result = solve(document)
    store = document["store"]
    if (set(store) != {"storeCode", "orderType", "beType"} or
            store["orderType"] != 1 or store["beType"] != 1 or
            not isinstance(store["storeCode"], str) or not store["storeCode"].isdigit()):
        raise ValueError("本版仅支持指定门店、即时到店自取。")
    offers = {offer["id"]: offer for offer in document["offers"]}
    budget = money(document["budget_yuan"], "budget_yuan")
    for candidate in result["plans"]:
        items = []
        for oid in candidate["offer_ids"]:
            value = offers[oid].get("quote_items")
            if not isinstance(value, list) or not value:
                raise ValueError("每个报价候选必须包含非空 quote_items。")
            for item in value:
                if (not isinstance(item, dict) or not isinstance(item.get("productCode"), str) or
                        not item["productCode"].isdigit() or
                        isinstance(item.get("quantity"), bool) or
                        not isinstance(item.get("quantity"), int) or item["quantity"] < 1):
                    raise ValueError("quote_items 的商品编码或数量无效。")
                items.append(item)
        try:
            response = business_response(client.call("calculate-price", {**store, "items": items}))
            candidate.update(checked_quote(response["data"], items, budget))
            candidate["quoted_at"] = response.get("datetime")
            candidate["limitations"] = ["总价与顶层商品数量已核验；套餐子项及指定券使用情况未在报价回执回显。"]
        except (MCPError, KeyError, TypeError) as exc:
            candidate["status"] = "quote_failed"
            candidate["error"] = str(exc) if isinstance(exc, MCPError) else "报价格式变化，无法确认。"
    result["store"] = store
    result["next_step"] = "只展示 verified_price 为核验通过；其余需调整候选或重新核验。"
    return result


def main():
    parser = argparse.ArgumentParser(description="麦麦预算实时价格核验（只读）")
    parser.add_argument("input", help="UTF-8 候选 JSON 文件")
    args = parser.parse_args()
    token = os.environ.get("MCD_MCP_TOKEN")
    if not token:
        parser.exit(2, "请在环境变量 MCD_MCP_TOKEN 中配置凭证。\n")
    try:
        with open(args.input, encoding="utf-8-sig") as file:
            document = json.load(file)
        client = Client(token)
        client.initialize()
        print(json.dumps(quote_plans(document, client), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError, MCPError) as exc:
        parser.exit(2, (str(exc) if isinstance(exc, MCPError) else "候选输入无效。") + "\n")


if __name__ == "__main__":
    main()
