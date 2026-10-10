"""Enumerate a small, agent-prepared set of offers; every result needs a live quote."""
import argparse
from decimal import Decimal, InvalidOperation
import itertools
import json


def number(value, field):
    if value is None or isinstance(value, bool):
        raise ValueError(f"{field} 必须是非负数。")
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"{field} 必须是非负数。") from None
    if not result.is_finite() or result < 0:
        raise ValueError(f"{field} 必须是有限非负数。")
    return result


def money(value, field):
    result = number(value, field)
    if result != result.quantize(Decimal("0.01")):
        raise ValueError(f"{field} 最多两位小数，单位为元。")
    return result


def solve(document):
    budget = money(document["budget_yuan"], "budget_yuan")
    if budget <= 0:
        raise ValueError("预算必须大于零。")
    for field in ("require_side", "require_drink"):
        if not isinstance(document.get(field, False), bool):
            raise ValueError(f"{field} 必须是布尔值。")
    offers = document["offers"]
    if not isinstance(offers, list) or len(offers) > 60:
        raise ValueError("候选 offers 必须为数组且不超过 60 项。")
    ids = set()
    groups = {"main": [], "side": [], "drink": []}
    for offer in offers:
        oid = offer["id"]
        if not isinstance(oid, str) or not oid or oid in ids:
            raise ValueError("候选 id 必须是唯一非空字符串。")
        ids.add(oid)
        if offer["category"] not in groups:
            raise ValueError("category 只允许 main、side、drink。")
        money(offer["price_yuan"], "price_yuan")
        if not offer.get("price_source"):
            raise ValueError("候选必须注明 price_source。")
        includes = offer.get("includes", [])
        if not isinstance(includes, list) or any(x not in groups for x in includes):
            raise ValueError("includes 只允许 main、side、drink。")
        for field in ("energy_kcal", "protein_g"):
            if offer.get(field) is not None:
                number(offer[field], field)
        coupons = offer.get("coupon_ids", [])
        if (not isinstance(coupons, list) or
                any(not isinstance(x, str) or not x for x in coupons) or
                len(coupons) != len(set(coupons))):
            raise ValueError("coupon_ids 必须是无重复的非空字符串数组。")
        groups[offer["category"]].append(offer)
    min_protein = (number(document["min_protein_g"], "min_protein_g")
                   if document.get("min_protein_g") is not None else None)
    max_energy = (number(document["max_energy_kcal"], "max_energy_kcal")
                  if document.get("max_energy_kcal") is not None else None)
    plans = []
    # Keep over-estimate candidates: coupon combinations may quote below budget.
    for main, side, drink in itertools.product(groups["main"], [None] + groups["side"],
                                                [None] + groups["drink"]):
        selected = [x for x in (main, side, drink) if x is not None]
        coverage = {main["category"], *main.get("includes", [])}
        if side and "side" in coverage or drink and "drink" in coverage:
            continue
        coverage.update(x["category"] for x in selected)
        if document.get("require_side") and "side" not in coverage:
            continue
        if document.get("require_drink") and "drink" not in coverage:
            continue
        coupons = [c for x in selected for c in x.get("coupon_ids", [])]
        if len(coupons) != len(set(coupons)):
            continue
        total = sum((money(x["price_yuan"], "price_yuan") for x in selected), Decimal(0))
        nutrition = {}
        for field in ("energy_kcal", "protein_g"):
            nutrition[field] = (sum((number(x[field], field) for x in selected), Decimal(0))
                                if all(x.get(field) is not None for x in selected) else None)
        if min_protein is not None and (nutrition["protein_g"] is None or
                                        nutrition["protein_g"] < min_protein):
            continue
        if max_energy is not None and (nutrition["energy_kcal"] is None or
                                       nutrition["energy_kcal"] > max_energy):
            continue
        plans.append({"offer_ids": [x["id"] for x in selected],
                      "names": [x["name"] for x in selected],
                      "estimated_total_yuan": str(total.quantize(Decimal("0.01"))),
                      "estimated_within_budget": total <= budget,
                      "energy_kcal": str(nutrition["energy_kcal"]) if nutrition["energy_kcal"] is not None else None,
                      "protein_g": str(nutrition["protein_g"]) if nutrition["protein_g"] is not None else None,
                      "coverage": sorted(coverage), "status": "needs_live_quote"})
    def price(p):
        return Decimal(p["estimated_total_yuan"])
    ordered = sorted(plans, key=lambda p: (not p["estimated_within_budget"], price(p), p["offer_ids"]))
    chosen = []
    if ordered:
        modes = [("省钱候选", ordered),
                 ("蛋白质优先候选", sorted([p for p in plans if p["protein_g"] is not None],
                   key=lambda p: (not p["estimated_within_budget"], -Decimal(p["protein_g"]), price(p)))),
                 ("组合丰富候选", sorted(plans,
                   key=lambda p: (not p["estimated_within_budget"], -len(p["coverage"]), price(p))))]
        seen = set()
        for label, candidates in modes:
            for candidate in candidates:
                key = tuple(candidate["offer_ids"])
                if key not in seen:
                    seen.add(key)
                    chosen.append({"reason": label, **candidate})
                    break
    return {"budget_yuan": str(budget), "candidate_count": len(plans), "plans": chosen,
            "scope": "输入候选集，一个主食或套餐加可选小食、饮料；并非全菜单最优。",
            "next_step": "用 calculate-price 核验各方案，淘汰实际应付金额超预算的方案。"}


def main():
    parser = argparse.ArgumentParser(description="麦麦预算候选计算；结果需要实时价格核验")
    parser.add_argument("input", help="UTF-8 候选 JSON")
    args = parser.parse_args()
    try:
        with open(args.input, encoding="utf-8-sig") as file:
            result = solve(json.load(file))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError):
        parser.exit(2, "候选输入无效；请检查格式、金额、营养数据及必填字段。\n")


if __name__ == "__main__":
    main()
