window.GOURMET_SNAPSHOTS = [
  {
    "mode": "snapshot",
    "captured_at": "2026-10-17T02:14:12+08:00",
    "store": {
      "code": "已脱敏",
      "name": "南京某门店（名称与地址已脱敏）",
      "address": "（门店名与地址已脱敏）",
      "city": "南京"
    },
    "source": {
      "tools": [
        "query-nearby-stores",
        "query-meals",
        "query-meal-detail",
        "calculate-price",
        "now-time-info"
      ],
      "note": "2026-10-17 02:13（北京时间）通过官方 MCP 实时核价后存为历史快照。所有金额为 calculate-price 返回的整数分。"
    },
    "scope": {
      "note": "同店同时刻对比「同样的东西：巨无霸 + 中薯条 + 中杯可乐」两条点法。套餐内饮料使用套餐内部 SKU（3050），单品直选用可单点 SKU（9900008751）——两者等价，但 3050 单独核价为 0 分，属套餐内部构成项。"
    },
    "evidence": {
      "per_item_cents": {
        "1100": 2550,
        "4810": 1350,
        "9900008751": 950,
        "3050": 0
      },
      "single_pick_cents": 4850,
      "combo_cents": 3650,
      "note": "3050 单点核价为 0，说明它是套餐内部 SKU；基线篮子不能用它，否则会算出偏小的省钱数字。"
    },
    "plans": [
      {
        "id": "single-pick",
        "name": "单品直选",
        "variant": "巨无霸 + 中薯条 + 可乐（单点）",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1100",
            "name": "巨无霸",
            "quantity": 1,
            "kind": "main",
            "spicy": false
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "is_fries": true
          },
          {
            "code": "9900008751",
            "name": "可乐",
            "quantity": 1,
            "kind": "drink",
            "ice": "standard",
            "sugar": "regular"
          }
        ],
        "price_cents": 4850,
        "spicy": false,
        "nutrition_missing": true,
        "energy_kcal": null,
        "sodium_mg": null,
        "protein_g": null,
        "quote_tool": "calculate-price"
      },
      {
        "id": "combo-3pc",
        "name": "巨无霸三件套",
        "variant": "套餐（巨无霸 + 中薯条 + 可乐中杯）",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1100",
            "name": "巨无霸",
            "quantity": 1,
            "kind": "main",
            "spicy": false
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "is_fries": true
          },
          {
            "code": "3050",
            "name": "可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "ice": "standard",
            "sugar": "regular"
          }
        ],
        "price_cents": 3650,
        "spicy": false,
        "nutrition_missing": true,
        "energy_kcal": null,
        "sodium_mg": null,
        "protein_g": null,
        "quote_tool": "calculate-price"
      }
    ],
    "baseline_plan_id": "single-pick"
  },
  {
    "mode": "snapshot",
    "fulfillment": {
      "channel": "pickup"
    },
    "store": {
      "code": "已脱敏",
      "name": "南京某门店（名称与地址已脱敏）",
      "address": "（门店名与地址已脱敏）",
      "city": "南京",
      "address_checked_at": "2026-10-13T16:49:03.901391+00:00",
      "address_source": "（来源隐藏）"
    },
    "captured_at": "2026-10-13T16:49:08+00:00",
    "source": "麦当劳官方 MCP：calculate-price + list-nutrition-foods",
    "scope": "仅比较本轮候选；不保证全菜单最低价；营养为标准份量的单品加总。",
    "plans": [
      {
        "id": "9900005456-4810-3050",
        "name": "麦辣鸡腿汉堡三件套",
        "variant": "中薯条 · 可乐中杯",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1440",
            "name": "麦辣鸡腿汉堡",
            "quantity": 1,
            "kind": "main",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": null
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": true,
            "sugar": null
          },
          {
            "code": "3050",
            "name": "可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "customizations": [
              "去冰"
            ],
            "ice": "none",
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": "regular"
          }
        ],
        "price_cents": 3350,
        "spicy": true,
        "nutrition_missing": [],
        "coupon_requested": false,
        "take_way_options": [
          {
            "code": "eat-in",
            "title": "堂食",
            "subtitle": "店内用餐"
          },
          {
            "code": "take-in-store",
            "title": "外带",
            "subtitle": "店内自提"
          }
        ],
        "fees_cents": {
          "deliveryPrice": null,
          "packingPrice": null,
          "tablewarePrice": null
        },
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 921.0,
        "sodium_mg": 1373.0,
        "protein_g": 28.0
      },
      {
        "id": "9900005456-4810-3071",
        "name": "麦辣鸡腿汉堡三件套",
        "variant": "中薯条 · 无糖可口可乐中杯",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1440",
            "name": "麦辣鸡腿汉堡",
            "quantity": 1,
            "kind": "main",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": null
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": true,
            "sugar": null
          },
          {
            "code": "3071",
            "name": "无糖可口可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "customizations": [
              "去冰"
            ],
            "ice": "none",
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": "zero"
          }
        ],
        "price_cents": 3350,
        "spicy": true,
        "nutrition_missing": [],
        "coupon_requested": false,
        "take_way_options": [
          {
            "code": "eat-in",
            "title": "堂食",
            "subtitle": "店内用餐"
          },
          {
            "code": "take-in-store",
            "title": "外带",
            "subtitle": "店内自提"
          }
        ],
        "fees_cents": {
          "deliveryPrice": null,
          "packingPrice": null,
          "tablewarePrice": null
        },
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 774.0,
        "sodium_mg": 1408.0,
        "protein_g": 28.0
      },
      {
        "id": "9900005464-4810-3050",
        "name": "双层吉士汉堡中套餐",
        "variant": "中薯条 · 可乐中杯",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1120",
            "name": "双层吉士汉堡",
            "quantity": 1,
            "kind": "main",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": null
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": true,
            "sugar": null
          },
          {
            "code": "3050",
            "name": "可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "customizations": [
              "去冰"
            ],
            "ice": "none",
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": "regular"
          }
        ],
        "price_cents": 3400,
        "spicy": false,
        "nutrition_missing": [],
        "coupon_requested": false,
        "take_way_options": [
          {
            "code": "eat-in",
            "title": "堂食",
            "subtitle": "店内用餐"
          },
          {
            "code": "take-in-store",
            "title": "外带",
            "subtitle": "店内自提"
          }
        ],
        "fees_cents": {
          "deliveryPrice": null,
          "packingPrice": null,
          "tablewarePrice": null
        },
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 865.0,
        "sodium_mg": 1182.0,
        "protein_g": 31.0
      },
      {
        "id": "9900005464-4810-3071",
        "name": "双层吉士汉堡中套餐",
        "variant": "中薯条 · 无糖可口可乐中杯",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1120",
            "name": "双层吉士汉堡",
            "quantity": 1,
            "kind": "main",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": null
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": true,
            "sugar": null
          },
          {
            "code": "3071",
            "name": "无糖可口可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "customizations": [
              "去冰"
            ],
            "ice": "none",
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": "zero"
          }
        ],
        "price_cents": 3400,
        "spicy": false,
        "nutrition_missing": [],
        "coupon_requested": false,
        "take_way_options": [
          {
            "code": "eat-in",
            "title": "堂食",
            "subtitle": "店内用餐"
          },
          {
            "code": "take-in-store",
            "title": "外带",
            "subtitle": "店内自提"
          }
        ],
        "fees_cents": {
          "deliveryPrice": null,
          "packingPrice": null,
          "tablewarePrice": null
        },
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 718.0,
        "sodium_mg": 1217.0,
        "protein_g": 31.0
      }
    ]
  },
  {
    "mode": "snapshot",
    "fulfillment": {
      "channel": "pickup"
    },
    "store": {
      "code": "已脱敏",
      "name": "南京某门店（名称与地址已脱敏）",
      "address": "（门店名与地址已脱敏）",
      "city": "南京",
      "address_checked_at": "2026-10-13T16:43:12.911097+00:00",
      "address_source": "（来源隐藏）"
    },
    "captured_at": "2026-10-13T16:05:17+00:00",
    "source": "麦当劳官方 MCP：calculate-price + list-nutrition-foods",
    "scope": "仅比较本轮候选；不保证全菜单最低价；营养为标准份量的单品加总。",
    "plans": [
      {
        "id": "9900005456-4810-3050",
        "name": "麦辣鸡腿汉堡三件套",
        "variant": "中薯条 · 可乐中杯",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1440",
            "name": "麦辣鸡腿汉堡",
            "quantity": 1,
            "kind": "main",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": null
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": true,
            "sugar": null
          },
          {
            "code": "3050",
            "name": "可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "customizations": [
              "去冰"
            ],
            "ice": "none",
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": "regular"
          }
        ],
        "price_cents": 3350,
        "spicy": true,
        "nutrition_missing": [],
        "coupon_requested": false,
        "take_way_options": [
          {
            "code": "eat-in",
            "title": "堂食",
            "subtitle": "店内用餐"
          },
          {
            "code": "take-in-store",
            "title": "外带",
            "subtitle": "店内自提"
          }
        ],
        "fees_cents": {
          "deliveryPrice": null,
          "packingPrice": null,
          "tablewarePrice": null
        },
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 921.0,
        "sodium_mg": 1373.0,
        "protein_g": 28.0
      },
      {
        "id": "9900005456-4810-3071",
        "name": "麦辣鸡腿汉堡三件套",
        "variant": "中薯条 · 无糖可口可乐中杯",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1440",
            "name": "麦辣鸡腿汉堡",
            "quantity": 1,
            "kind": "main",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": null
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": true,
            "sugar": null
          },
          {
            "code": "3071",
            "name": "无糖可口可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "customizations": [
              "去冰"
            ],
            "ice": "none",
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": "zero"
          }
        ],
        "price_cents": 3350,
        "spicy": true,
        "nutrition_missing": [],
        "coupon_requested": false,
        "take_way_options": [
          {
            "code": "eat-in",
            "title": "堂食",
            "subtitle": "店内用餐"
          },
          {
            "code": "take-in-store",
            "title": "外带",
            "subtitle": "店内自提"
          }
        ],
        "fees_cents": {
          "deliveryPrice": null,
          "packingPrice": null,
          "tablewarePrice": null
        },
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 774.0,
        "sodium_mg": 1408.0,
        "protein_g": 28.0
      },
      {
        "id": "9900005464-4810-3050",
        "name": "双层吉士汉堡中套餐",
        "variant": "中薯条 · 可乐中杯",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1120",
            "name": "双层吉士汉堡",
            "quantity": 1,
            "kind": "main",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": null
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": true,
            "sugar": null
          },
          {
            "code": "3050",
            "name": "可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "customizations": [
              "去冰"
            ],
            "ice": "none",
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": "regular"
          }
        ],
        "price_cents": 3400,
        "spicy": false,
        "nutrition_missing": [],
        "coupon_requested": false,
        "take_way_options": [
          {
            "code": "eat-in",
            "title": "堂食",
            "subtitle": "店内用餐"
          },
          {
            "code": "take-in-store",
            "title": "外带",
            "subtitle": "店内自提"
          }
        ],
        "fees_cents": {
          "deliveryPrice": null,
          "packingPrice": null,
          "tablewarePrice": null
        },
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 865.0,
        "sodium_mg": 1182.0,
        "protein_g": 31.0
      },
      {
        "id": "9900005464-4810-3071",
        "name": "双层吉士汉堡中套餐",
        "variant": "中薯条 · 无糖可口可乐中杯",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1120",
            "name": "双层吉士汉堡",
            "quantity": 1,
            "kind": "main",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": null
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "customizations": [],
            "ice": null,
            "nutrition_customized": false,
            "is_fries": true,
            "sugar": null
          },
          {
            "code": "3071",
            "name": "无糖可口可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "customizations": [
              "去冰"
            ],
            "ice": "none",
            "nutrition_customized": false,
            "is_fries": false,
            "sugar": "zero"
          }
        ],
        "price_cents": 3400,
        "spicy": false,
        "nutrition_missing": [],
        "coupon_requested": false,
        "take_way_options": [
          {
            "code": "eat-in",
            "title": "堂食",
            "subtitle": "店内用餐"
          },
          {
            "code": "take-in-store",
            "title": "外带",
            "subtitle": "店内自提"
          }
        ],
        "fees_cents": {
          "deliveryPrice": null,
          "packingPrice": null,
          "tablewarePrice": null
        },
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 718.0,
        "sodium_mg": 1217.0,
        "protein_g": 31.0
      }
    ]
  },
  {
    "mode": "snapshot",
    "store": {
      "code": "已脱敏",
      "name": "南京某门店（名称与地址已脱敏）",
      "address": "（门店名与地址已脱敏）",
      "city": "南京",
      "address_checked_at": "2026-10-13T16:43:12.911097+00:00",
      "address_source": "（来源隐藏）"
    },
    "captured_at": "2026-10-13T14:14:10+00:00",
    "source": "麦当劳官方 MCP：calculate-price + list-nutrition-foods",
    "scope": "仅比较本轮候选；不保证全菜单最低价；营养为标准份量的单品加总。",
    "plans": [
      {
        "id": "chicken-classic",
        "name": "麦辣鸡腿汉堡三件套",
        "variant": "中薯条 · 可乐",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1440",
            "name": "麦辣鸡腿汉堡",
            "quantity": 1,
            "kind": "main",
            "is_fries": false
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "is_fries": true
          },
          {
            "code": "3050",
            "name": "可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "is_fries": false,
            "sugar": "regular"
          }
        ],
        "price_cents": 3350,
        "spicy": true,
        "nutrition_missing": [],
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 921.0,
        "sodium_mg": 1373.0,
        "protein_g": 28.0
      },
      {
        "id": "chicken-corn",
        "name": "麦辣鸡腿汉堡三件套",
        "variant": "玉米杯 · 无糖可乐",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1440",
            "name": "麦辣鸡腿汉堡",
            "quantity": 1,
            "kind": "main",
            "is_fries": false
          },
          {
            "code": "4437",
            "name": "小杯玉米杯",
            "quantity": 1,
            "kind": "side",
            "is_fries": false
          },
          {
            "code": "3071",
            "name": "无糖可口可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "is_fries": false,
            "sugar": "zero"
          }
        ],
        "price_cents": 3200,
        "spicy": true,
        "nutrition_missing": [],
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 538.0,
        "sodium_mg": 1244.0,
        "protein_g": 26.0
      },
      {
        "id": "cheese-classic",
        "name": "双层吉士汉堡中套餐",
        "variant": "中薯条 · 可乐",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1120",
            "name": "双层吉士汉堡",
            "quantity": 1,
            "kind": "main",
            "is_fries": false
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "is_fries": true
          },
          {
            "code": "3050",
            "name": "可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "is_fries": false,
            "sugar": "regular"
          }
        ],
        "price_cents": 3350,
        "spicy": false,
        "nutrition_missing": [],
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 865.0,
        "sodium_mg": 1182.0,
        "protein_g": 31.0
      },
      {
        "id": "cheese-corn",
        "name": "双层吉士汉堡中套餐",
        "variant": "玉米杯 · 无糖可乐",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1120",
            "name": "双层吉士汉堡",
            "quantity": 1,
            "kind": "main",
            "is_fries": false
          },
          {
            "code": "4437",
            "name": "小杯玉米杯",
            "quantity": 1,
            "kind": "side",
            "is_fries": false
          },
          {
            "code": "3071",
            "name": "无糖可口可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "is_fries": false,
            "sugar": "zero"
          }
        ],
        "price_cents": 3200,
        "spicy": false,
        "nutrition_missing": [],
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 482.0,
        "sodium_mg": 1053.0,
        "protein_g": 29.0
      },
      {
        "id": "fish-classic",
        "name": "麦香鱼中套餐",
        "variant": "中薯条 · 可乐",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1600",
            "name": "麦香鱼",
            "quantity": 1,
            "kind": "main",
            "is_fries": false
          },
          {
            "code": "4810",
            "name": "中薯条",
            "quantity": 1,
            "kind": "side",
            "is_fries": true
          },
          {
            "code": "3050",
            "name": "可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "is_fries": false,
            "sugar": "regular"
          }
        ],
        "price_cents": 3400,
        "spicy": false,
        "nutrition_missing": [],
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 761.0,
        "sodium_mg": 721.0,
        "protein_g": 20.0
      },
      {
        "id": "fish-corn",
        "name": "麦香鱼中套餐",
        "variant": "玉米杯 · 无糖可乐",
        "store_code": "已脱敏",
        "items": [
          {
            "code": "1600",
            "name": "麦香鱼",
            "quantity": 1,
            "kind": "main",
            "is_fries": false
          },
          {
            "code": "4437",
            "name": "小杯玉米杯",
            "quantity": 1,
            "kind": "side",
            "is_fries": false
          },
          {
            "code": "3071",
            "name": "无糖可口可乐中杯",
            "quantity": 1,
            "kind": "drink",
            "is_fries": false,
            "sugar": "zero"
          }
        ],
        "price_cents": 3250,
        "spicy": false,
        "nutrition_missing": [],
        "coupon_applied": false,
        "quote_tool": "calculate-price",
        "energy_kcal": 378.0,
        "sodium_mg": 592.0,
        "protein_g": 18.0
      }
    ]
  }
];
window.GOURMET_DATA = window.GOURMET_SNAPSHOTS[0];
