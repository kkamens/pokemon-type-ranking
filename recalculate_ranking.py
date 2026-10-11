from __future__ import annotations

import html
import itertools
import json
import math
import re
import shutil
from pathlib import Path

ROOT = Path(r"D:\ycx\pokemon_type_rank")
HTML_PATH = ROOT / "index.html"
BACKUP_PATH = ROOT / "_backup" / "index_before_171_target_recalculation.html"

TYPES = [
    "一般", "火", "水", "电", "草", "冰", "格斗", "毒", "地面",
    "飞行", "超能力", "虫", "岩石", "幽灵", "龙", "恶", "钢", "妖精",
]

# 第六世代起沿用的18属性相克表：只列非1倍关系。
SUPER = {
    "一般": [],
    "火": ["草", "冰", "虫", "钢"],
    "水": ["火", "地面", "岩石"],
    "电": ["水", "飞行"],
    "草": ["水", "地面", "岩石"],
    "冰": ["草", "地面", "飞行", "龙"],
    "格斗": ["一般", "冰", "岩石", "恶", "钢"],
    "毒": ["草", "妖精"],
    "地面": ["火", "电", "毒", "岩石", "钢"],
    "飞行": ["草", "格斗", "虫"],
    "超能力": ["格斗", "毒"],
    "虫": ["草", "超能力", "恶"],
    "岩石": ["火", "冰", "飞行", "虫"],
    "幽灵": ["超能力", "幽灵"],
    "龙": ["龙"],
    "恶": ["超能力", "幽灵"],
    "钢": ["冰", "岩石", "妖精"],
    "妖精": ["格斗", "龙", "恶"],
}
RESISTED = {
    "一般": ["岩石", "钢"],
    "火": ["火", "水", "岩石", "龙"],
    "水": ["水", "草", "龙"],
    "电": ["电", "草", "龙"],
    "草": ["火", "草", "毒", "飞行", "虫", "龙", "钢"],
    "冰": ["火", "水", "冰", "钢"],
    "格斗": ["毒", "飞行", "超能力", "虫", "妖精"],
    "毒": ["毒", "地面", "岩石", "幽灵"],
    "地面": ["草", "虫"],
    "飞行": ["电", "岩石", "钢"],
    "超能力": ["超能力", "钢"],
    "虫": ["火", "格斗", "毒", "飞行", "幽灵", "钢", "妖精"],
    "岩石": ["格斗", "地面", "钢"],
    "幽灵": ["恶"],
    "龙": ["钢"],
    "恶": ["格斗", "恶", "妖精"],
    "钢": ["火", "水", "电", "钢"],
    "妖精": ["火", "毒", "钢"],
}
IMMUNE = {
    "一般": ["幽灵"],
    "火": [], "水": [],
    "电": ["地面"],
    "草": [], "冰": [],
    "格斗": ["幽灵"],
    "毒": ["钢"],
    "地面": ["飞行"],
    "飞行": [],
    "超能力": ["恶"],
    "虫": [], "岩石": [],
    "幽灵": ["一般"],
    "龙": ["妖精"],
    "恶": [], "钢": [], "妖精": [],
}

TYPE_ICON_URLS = {
    "一般": "https://aka.doubaocdn.com/s/EzkrtPUaM2",
    "火": "https://aka.doubaocdn.com/s/NUdr2JcU8J",
    "水": "https://aka.doubaocdn.com/s/Z4wE2hHv4z",
    "电": "https://aka.doubaocdn.com/s/kaJ4ggjxR9",
    "草": "https://aka.doubaocdn.com/s/FL4sH3TE1T",
    "冰": "https://aka.doubaocdn.com/s/xTvWPgBJ2u",
    "格斗": "https://aka.doubaocdn.com/s/7vaTDaxq9c",
    "毒": "https://aka.doubaocdn.com/s/VYYnK1t3zf",
    "地面": "https://aka.doubaocdn.com/s/Xva2HuinHe",
    "飞行": "https://aka.doubaocdn.com/s/W1PWF484M1",
    "超能力": "https://aka.doubaocdn.com/s/FELRNrk4Ts",
    "虫": "https://aka.doubaocdn.com/s/JjtAxXkqTj",
    "岩石": "https://aka.doubaocdn.com/s/zzbEs5NgIr",
    "幽灵": "https://aka.doubaocdn.com/s/rbWE5urv3u",
    "龙": "https://aka.doubaocdn.com/s/czX2r4q20m",
    "恶": "https://aka.doubaocdn.com/s/y8IFdV1851",
    "钢": "https://aka.doubaocdn.com/s/ovVOetZ1de",
    "妖精": "https://aka.doubaocdn.com/s/FD6l4zVDX2",
}


def multiplier(attacking: str, defending: str) -> float:
    if defending in IMMUNE[attacking]:
        return 0.0
    if defending in SUPER[attacking]:
        return 2.0
    if defending in RESISTED[attacking]:
        return 0.5
    return 1.0


def attack_score(mult: float) -> float:
    if mult == 0:
        return -4.5
    base = math.log2(mult)
    if base > 0:
        return base + 0.5
    if base < 0:
        return base - 0.5
    return 0.0


def defense_score(mult: float) -> float:
    if mult == 0:
        return 4.5
    base = -math.log2(mult)
    if base > 0:
        return base + 0.5
    if base < 0:
        return base - 0.5
    return 0.0


def combo_name(combo: tuple[str, ...]) -> str:
    return "/".join(combo)


def clean_number(value: float) -> float:
    # 数据中保留足够精度用于稳定排序；前端统一显示至2位小数。
    return round(value, 9)


def calculate_rows() -> list[dict]:
    defenders = [(t,) for t in TYPES] + list(itertools.combinations(TYPES, 2))
    candidates = [(t,) for t in TYPES] + list(itertools.combinations(TYPES, 2))
    assert len(defenders) == 171 and len(candidates) == 171

    rows = []
    for candidate in candidates:
        attack_raw = 0.0
        for defender in defenders:
            best = max(
                math.prod(multiplier(attacker, d) for d in defender)
                for attacker in candidate
            )
            attack_raw += attack_score(best)

        # 保留打击端对 171 种防守组合的原始总分。
        attack_aligned = attack_raw

        resist_raw = 0.0
        for attacker in TYPES:
            incoming = math.prod(multiplier(attacker, d) for d in candidate)
            resist_raw += defense_score(incoming)

        # 抗击端原始样本数为 18；乘以 171/18=9.5，对齐打击端的 171 项尺度。
        resist_aligned = resist_raw * 9.5
        total = attack_aligned + resist_aligned
        balance = -abs(attack_aligned - resist_aligned)
        rows.append({
            "name": combo_name(candidate),
            "atk": clean_number(attack_aligned),
            "def": clean_number(resist_aligned),
            "total": clean_number(total),
            "bal": clean_number(balance),
            "attack_raw": clean_number(attack_raw),
            "defense_raw": clean_number(resist_raw),
            "kind": "单" if len(candidate) == 1 else "双",
        })
    return rows


def rank_tuple(row: dict) -> tuple:
    return (row["total"], row["bal"], row["atk"], row["def"])


def js_data(rows: list[dict]) -> tuple[str, str]:
    fields = ("name", "atk", "def", "total", "bal")
    singles = [{k: r[k] for k in fields} for r in rows if r["kind"] == "单"]
    duals = [{k: r[k] for k in fields} for r in rows if r["kind"] == "双"]
    singles.sort(key=rank_tuple, reverse=True)
    duals.sort(key=rank_tuple, reverse=True)
    return (
        json.dumps(singles, ensure_ascii=False, separators=(",", ":")),
        json.dumps(duals, ensure_ascii=False, separators=(",", ":")),
    )


def pad_name(t: str) -> str:
    return ("　" * max(0, 3 - len(t))) + t


def entry_html(name: str) -> str:
    parts = name.split("/")
    cls = "entry"
    if len(parts) == 1:
        t = parts[0]
        inner = (
            '<span class="a1"></span><span class="sep"></span>'
            f'<span class="a2"><img class="qi" src="{TYPE_ICON_URLS[t]}" alt="{html.escape(t)}">'
            f'<span class="nm">{html.escape(pad_name(t))}</span></span>'
        )
    else:
        a, b = parts
        inner = (
            f'<span class="a1"><img class="qi" src="{TYPE_ICON_URLS[a]}" alt="{html.escape(a)}">'
            f'<span class="nm">{html.escape(pad_name(a))}</span></span>'
            '<span class="sep">/</span>'
            f'<span class="a2"><img class="qi" src="{TYPE_ICON_URLS[b]}" alt="{html.escape(b)}">'
            f'<span class="nm">{html.escape(pad_name(b))}</span></span>'
        )
    return f'<span class="{cls}"><span class="ai">{inner}</span></span>'


def tied_rows(rows: list[dict], metric: str, strongest: bool) -> list[dict]:
    extreme = (max if strongest else min)(r[metric] for r in rows)
    tied = [r for r in rows if math.isclose(r[metric], extreme, abs_tol=1e-8)]
    tied.sort(key=lambda r: (rank_tuple(r), r["name"]), reverse=strongest)
    return tied


def group_html(rows: list[dict], metric: str, strongest: bool) -> str:
    tied = tied_rows(rows, metric, strongest)
    return "<br>".join(entry_html(r["name"]) for r in tied)


def build_quick_table(rows: list[dict]) -> str:
    singles = [r for r in rows if r["kind"] == "单"]
    duals = [r for r in rows if r["kind"] == "双"]
    metrics = [("综合", "total"), ("平衡", "bal"), ("打击", "atk"), ("抗击", "def")]
    out = [
        '<table class="quick-table"><thead><tr><th>类型</th><th>强弱</th>'
        '<th>全部属性</th><th>双属性</th><th>单属性</th></tr></thead><tbody>'
    ]
    for label, metric in metrics:
        for idx, strongest in enumerate((True, False)):
            all_group = tied_rows(rows, metric, strongest)
            dual_group = tied_rows(duals, metric, strongest)
            single_group = tied_rows(singles, metric, strongest)
            all_names = [r["name"] for r in all_group]
            dual_names = [r["name"] for r in dual_group]
            out.append("<tr>")
            if idx == 0:
                out.append(f'<td class="range" rowspan="2">{label}</td>')
            out.append(f'<td class="weak {"strongest" if strongest else "weakest"}">{"最强" if strongest else "最弱"}</td>')
            if all_names == dual_names:
                out.append(f'<td colspan="2">{group_html(rows, metric, strongest)}</td>')
            else:
                out.append(f'<td>{group_html(rows, metric, strongest)}</td>')
                out.append(f'<td class="qcol">{group_html(duals, metric, strongest)}</td>')
            out.append(f'<td class="qcol">{group_html(singles, metric, strongest)}</td>')
            out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def replace_once(text: str, pattern: str, replacement: str, flags: int = 0) -> str:
    new, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"expected one match, got {count}: {pattern[:80]}")
    return new


def main() -> None:
    source = HTML_PATH.read_text(encoding="utf-8")
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HTML_PATH, BACKUP_PATH)

    rows = calculate_rows()
    singles_json, duals_json = js_data(rows)
    quick = build_quick_table(rows)

    updated = source
    updated = replace_once(updated, r'<table class="quick-table">[\s\S]*?</table>', quick)
    updated = replace_once(updated, r'var SINGLES = \[[\s\S]*?\];\s*var DUALS = \[[\s\S]*?\];',
                           f'var SINGLES = {singles_json};\n  var DUALS = {duals_json};')

    # 单属性和双属性均直接使用预计算的平衡分，避免前端再次引入显示误差。
    updated = updated.replace(
        "return { name: r.name, atk: r.atk, def: r.def, total: r.total, bal: -Math.abs(r.atk - r.def), kind: '单', poke: p };",
        "return { name: r.name, atk: r.atk, def: r.def, total: r.total, bal: r.bal, kind: '单', poke: p };"
    )

    # 统一分值显示为最多2位小数，排名仍使用完整预计算精度。
    marker = "  function ranksFor(rows, key){"
    formatter = (
        "  function scoreFmt(v){\n"
        "    if (Math.abs(v) < 0.0000005) return '0';\n"
        "    return String(Math.round(v * 100) / 100);\n"
        "  }\n"
    )
    if "function scoreFmt" not in updated:
        updated = updated.replace(marker, formatter + marker)
    updated = updated.replace("var av = rankMode ? atkR[r.name] : r.atk;", "var av = rankMode ? atkR[r.name] : scoreFmt(r.atk);")
    updated = updated.replace("var dv = rankMode ? defR[r.name] : r.def;", "var dv = rankMode ? defR[r.name] : scoreFmt(r.def);")
    updated = updated.replace("var bv = rankMode ? balR[r.name] : r.bal;", "var bv = rankMode ? balR[r.name] : scoreFmt(r.bal);")
    updated = updated.replace("var tv = rankMode ? totR[r.name] : r.total;", "var tv = rankMode ? totR[r.name] : scoreFmt(r.total);")
    updated = updated.replace("var cls = function(v){ return rankMode ? 'rk' : (v >= 0 ? 'pos' : 'neg'); };",
                              "var cls = function(v){ return percentMode ? 'pct' : (rankMode ? 'rk' : (Number(v) >= 0 ? 'pos' : 'neg')); };")

    # Tooltip 同样使用统一格式。
    updated = updated.replace(
        "+ '抗击 ' + p.value[0] + ' · 打击 ' + p.value[1] + ' · 综合 ' + p.value[2] + String.fromCharCode(10)",
        "+ '抗击 ' + scoreFmt(p.value[0]) + ' · 打击 ' + scoreFmt(p.value[1]) + ' · 综合 ' + scoreFmt(p.value[2]) + String.fromCharCode(10)"
    )

    # 图表两轴均使用 171 项尺度；轴范围由当前 HTML 的独立更新流程维护。

    old_rules = re.compile(
        r'<li><b>打击得分</b>：[\s\S]*?</li>\s*'
        r'<li><b>抗击得分</b>：[\s\S]*?</li>\s*'
        r'<li><b>综合</b> =[\s\S]*?</li>\s*'
        r'<li><b>平衡</b> =[\s\S]*?</li>'
    )
    new_rules = (
        '<li><b>打击得分</b>：对全部 171 种防守属性组合逐项计分；双属性作为打击组合时，对每个目标取两种属性中更有利的倍率。所得原始总分直接作为打击得分，保留 171 项尺度。</li>\n'
        '      <li><b>抗击得分</b>：面对 18 种单属性来袭逐项计分后求和，再乘以 9.5（171 ÷ 18），折算为与 171 项打击端相同的尺度。</li>\n'
        '      <li><b>综合</b> = 打击得分 + 等效抗击得分，两端权重相等。</li>\n'
        '      <li><b>平衡</b> = −|打击得分 − 等效抗击得分|（越接近 0 越均衡）。</li>'
    )
    updated, n = old_rules.subn(new_rules, updated, count=1)
    updated = re.sub(r'<li>(?:<b>(?:排名|位次)</b>：)?[\s\S]*?按综合 → 平衡 → 打击 → 抗击[\s\S]*?</li>', '<li>全量数据表中并列时，按综合 → 平衡 → 打击 → 抗击依次比较显示位次。</li>', updated, count=1)
    if n != 1:
        raise RuntimeError(f"rules replacement failed: {n}")

    HTML_PATH.write_text(updated, encoding="utf-8")

    ranked = sorted(rows, key=rank_tuple, reverse=True)
    print(json.dumps({
        "count": len(rows),
        "singles": sum(r["kind"] == "单" for r in rows),
        "duals": sum(r["kind"] == "双" for r in rows),
        "top5": [{k: r[k] for k in ("name", "total", "bal", "atk", "def")} for r in ranked[:5]],
        "bottom5": [{k: r[k] for k in ("name", "total", "bal", "atk", "def")} for r in ranked[-5:]],
        "rock": next(r for r in rows if r["name"] == "岩石"),
        "attack_range": [min(r["atk"] for r in rows), max(r["atk"] for r in rows)],
        "defense_range": [min(r["def"] for r in rows), max(r["def"] for r in rows)],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
