# Meal Council · McDonald's China MCP

**"35 yuan, not spicy, regular cola with no ice, takeaway."** Say it once and compare a complete meal — an explicit regular-cola choice is never silently swapped for zero sugar, and when nothing fits it says so instead of selling you a lone soda.

[Try the demo in 30 seconds](https://polaris-smart.github.io/mcd-agent-gourmet/) · [中文](README.md)

![First screen: official per-order pricing, one answer, a copyable order card](docs/assets/hero.png)

**Try it in 30 seconds** — no account, token or install:

- Set the budget to **30 yuan**: nothing qualifies, and the page says so rather than counting a cola as a meal.
- Back to **35 yuan** and pick **regular cola, no ice**: only matching drinks and ice levels remain; the nutrition comparison never quietly switches you to zero sugar.
- Choose **not spicy**: only qualifying meals remain. The sodium cap is yours to set — a personal filter, not a health standard.
- Change a condition after picking a meal: the previous pick is cleared and must be re-confirmed.

![The full comparison opens only when you ask for it](docs/assets/results.png)

The browser compares historical snapshots entirely on your device: no credentials, no ordering, no trackers. Independent contest entry, not an official McDonald's product.

## How this relates to the McDonald's app

The app is where you **order**; this is where the decision gets settled **before** you open it.

- The app gives you one cart: you page through the menu and assemble the meal yourself. There is no "give me a few complete meals with the trade-off for each" entry point.
- The app will not tell you "nothing fits this budget". This does, and it adds **how much budget would actually be needed and how many meals that unlocks** (budget ladder, below).
- Nothing here claims coupons, redeems points, orders or pays — there is no cart. It has no reason to talk you into buying more.

## 0.4: it also explains why each rejected meal lost

- **Frontier explanations.** For each comparison axis (price & sodium / taste & sodium / multi-nutrient) every other candidate is reported as **dominated by which candidate, on which axis** — e.g. "from the price & sodium axis, why not cheese-classic: dominated by cheese-corn — lower price (¥32.00 vs ¥33.50); lower sodium (1053 mg vs 1182 mg)". Ties stay on the frontier; candidates with incomplete data are listed separately as excluded, never scored as zero.
- **Budget ladder.** When nothing fits, it no longer stops at a single "minimum needed" figure: it gives steps — "¥32.00 → 2 meals; ¥32.50 → 3; ¥33.50 → 5" — and states that **only the budget changes**; taste, side, drink and nutrition conditions are never relaxed.
- Both are explanations only: the tool never rewrites your conditions, never raises your budget on its own, and never produces a health score.

A complete meal comes first: a main, a side and a drink. Deterministic comparisons show lower cost, lower known sodium and closer taste matches among eligible candidates. Several criteria may select the same meal. Regular and zero-sugar cola are equal preference choices; an explicit preference is never silently replaced.

The browser demo includes three separate Nanjing restaurant snapshots, each with its own address, timestamp and **historical, officially priced meal configurations**. It needs no account or token. These are not current prices or dietary recommendations. Nothing is ordered or paid for.

For everyday use, install the Skill in WorkBuddy with your private McDonald's MCP connection, then describe the meal naturally: “35 yuan, not spicy, regular cola with no ice, takeaway near Tianyuan East Road in Nanjing. Show restaurant names and addresses so I can choose first.” The client passes identifiers between tools. The commands below are the developer interface. The latest complete WorkBuddy conversation flow still needs client acceptance testing.

```bash
python3 demo.py --budget 35 --taste spicy
python3 demo.py --budget 35 --taste no-spicy --sodium-limit 800
python3 -B -m unittest discover -s tests -v
```

Python 3.9+, standard library only. Live mode requires your own `MCD_MCP_TOKEN` in the local environment and an explicitly selected restaurant plan:

```bash
python3 demo.py --live --plan fixtures/plan.json
```

Live calls use the official menu, combo details, nutrition table and `calculate-price`. Failures stop the run; they never silently substitute demo data. Missing nutrition remains unknown. The default plan does not apply coupons. Only the configured candidates are compared, not the entire menu.

The Python/browser comparisons are deterministic functions, **not three independent LLMs**. The accompanying `SKILL.md` guides the client through understanding preferences, querying facts and explaining comparisons. The executable client only allows read/query/price tools.

Independent M-CODE 2026 entry. Not an official McDonald's product. MIT for original code; official materials retain their applicable terms. If you find the approach useful, a Star or actionable issue is welcome.

## v0.2.1: clearer provenance and trade-offs

The CLI prints source, store and timestamp to stderr even with JSON output. The web demo prominently labels historical prices. Price/sodium and taste/sodium comparisons retain non-dominated, eligible candidates with known sodium; energy and protein remain visible rather than being converted to an unsupported health score. These are six quoted candidates, not an exhaustive menu search.

Run `python3 demo.py --list-coupons --plan fixtures/plan.json` after confirming that store to see coupon titles and matching candidates. The explicit live flags `--coupon-title` and `--coupon-candidate` resolve private identifiers in memory. Ambiguous names and mismatches stop; no coupon is used by default. Successful live coupon pricing remains unverified.

## Version 0.3

Sugar preferences, official ice/ingredient customization, bounded combinations, explicit store selection, channel-aware coupon and pricing contexts, read-only points/coupon views, and multi-nutrient comparisons are implemented. Ingredient removal invalidates standard nutrition totals. The web demo includes three independent historical stores and optional browser-local preferences.

Pareto comparisons remove a candidate only when another is no worse in every chosen dimension and strictly better in at least one. Four-dimensional comparison can retain every candidate; it is not a unique balanced recommendation or a universal health ranking.

Version 0.3.1 adds `--my-coupons`: a read-only wallet report separating official status, validity dates, locally interpreted time windows and optional store/channel lookup. It preserves every coupon, handles weekday and overnight windows, labels unsupported text as unknown, and never treats matching names as stackable coupons. Use `--coupon-demo` for explicitly synthetic, offline examples. Store matching uses identifiers only in memory; actual savings still require official pricing. Do not buy something solely because a coupon is expiring.

Build the WorkBuddy distribution using `python3 scripts/build_skill_package.py --output /tmp/mcd-agent-gourmet-0.3.1.zip`. It is not yet submitted or listed. See [capability boundaries](references/mcp-capabilities.md) and [validation](docs/validation.md), including verified pickup customizations and unverified delivery pricing.
