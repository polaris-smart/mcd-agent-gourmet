# Meal Council · McDonald's China MCP

**When budget, taste and nutrition data disagree, see the trade-offs and make the final choice.**

[Try the demo](https://polaris-smart.github.io/mcd-agent-gourmet/) · [中文](README.md)

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

The Python/browser comparisons are deterministic functions, **not three independent LLMs**. The accompanying `SKILL.md` also describes optional role-based review in an AI client; that is not evidence of three models running in this program. The executable client only allows read/query/price tools.

Independent M-CODE 2026 entry. Not an official McDonald's product. MIT for original code; official materials retain their applicable terms. If you find the approach useful, a Star or actionable issue is welcome.

## v0.2.1: clearer provenance and trade-offs

The CLI prints source, store and timestamp to stderr even with JSON output. The web demo prominently labels historical prices. Price/sodium and taste/sodium comparisons retain non-dominated, eligible candidates with known sodium; energy and protein remain visible rather than being converted to an unsupported health score. These are six quoted candidates, not an exhaustive menu search.

Run `python3 demo.py --list-coupons --plan fixtures/plan.json` after confirming that store to see coupon titles and matching candidates. The explicit live flags `--coupon-title` and `--coupon-candidate` resolve private identifiers in memory. Ambiguous names and mismatches stop; no coupon is used by default. Successful live coupon pricing remains unverified.

## Version 0.3

Sugar preferences, official ice/ingredient customization, bounded combinations, explicit store selection, channel-aware coupon and pricing contexts, read-only points/coupon views, and multi-nutrient comparisons are implemented. Ingredient removal invalidates standard nutrition totals. The web demo includes three independent historical stores and optional browser-local preferences.

Pareto comparisons remove a candidate only when another is no worse in every chosen dimension and strictly better in at least one. Four-dimensional comparison can retain every candidate; it is not a unique balanced recommendation or a universal health ranking.

Build the WorkBuddy distribution using `python3 scripts/build_skill_package.py --output /tmp/mcd-agent-gourmet-0.3.0.zip`. It is not yet submitted or listed. See [capability boundaries](references/mcp-capabilities.md) and [validation](docs/validation.md), including verified pickup customizations and unverified delivery pricing.
