# Meal Council · McDonald's China MCP

**When budget, taste and nutrition data disagree, see the trade-offs and make the final choice.**

[Try the demo](https://polaris-smart.github.io/mcd-agent-gourmet/) · [中文](README.md)

A complete meal comes first: a main, a side and a drink. Three transparent rule-based reviewers independently compare cost, known sodium content and taste preference. They may disagree. The user chooses.

The browser demo uses six **historical, officially priced meal configurations**, captured on October 13, 2026 at a Nanjing restaurant. It needs no account or token. These are not current prices or dietary recommendations. Nothing is ordered or paid for.

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

The Python/browser reviewers are deterministic functions, **not three independent LLMs**. The accompanying `SKILL.md` describes how an AI client can delegate independent reviews of the same verified facts. The executable client only allows read/query/price tools.

Independent M-CODE 2026 entry. Not an official McDonald's product. MIT for original code; official materials retain their applicable terms. If you find the approach useful, a Star or actionable issue is welcome.

## v0.2.1: clearer provenance and trade-offs

The CLI prints source, store and timestamp to stderr even with JSON output. The web demo prominently labels historical prices. Price/sodium and taste/sodium comparisons retain non-dominated, eligible candidates with known sodium; energy and protein remain visible rather than being converted to an unsupported health score. These are six quoted candidates, not an exhaustive menu search.

Run `python3 demo.py --list-coupons` to see coupon titles and matching candidate IDs. The explicit live flags `--coupon-title` and `--coupon-candidate` resolve private identifiers in memory; ambiguous names and product mismatches stop. No coupon is used by default. Successful live coupon pricing remains unverified.
