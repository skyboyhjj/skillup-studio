"""
语言谱系树数据集构建脚本
========================
生成与 BAAI 知识树快照格式兼容的语言谱系树数据，
作为同态映射引擎的"第二块试验田"。

数据来源：
- 全球五大语系：印欧、汉藏、南岛、突厥、亚非
- 参考 Ethnologue / Glottolog 分类体系
- 五行分类：基于语言演化特征（扩张/融合/稳定/规则/适应）

输出格式：与 2026-07-30_snapshot.json 完全兼容
"""

import json
import os
from datetime import datetime

# ============================================================
# 五行分类映射（语言领域特化）
# ============================================================
# 木: 扩张性强、分支多、语音创新快
# 火: 交互密集、借用词多、融合性强
# 土: 结构稳定、语法保守、连续性强
# 金: 规则清晰、形态丰富、边界明确
# 水: 适应性强、变体多、吸收力强

# ============================================================
# 节点定义
# ============================================================

LANGUAGE_TREE = {
    "印欧语系": {
        "wuxing": "土",
        "depth": "L1",
        "subfamilies": {
            "日耳曼语族": {
                "wuxing": "金",
                "languages": [
                    ("英语", "水", "诺曼征服后分层吸收，词汇双源，语法简化"),
                    ("德语", "金", "格系统保持，强/弱动词规则清晰"),
                    ("荷兰语", "木", "词尾辅音清化，创新性语音变化"),
                    ("瑞典语", "水", "格系统简化，声调创新"),
                    ("挪威语", "水", "两种书面标准，适应性分化"),
                    ("丹麦语", "水", "喉塞音创新，声门化特征"),
                    ("冰岛语", "土", "古诺尔斯语直系，语法极度保守"),
                ]
            },
            "罗曼语族": {
                "wuxing": "火",
                "languages": [
                    ("法语", "火", "广泛借用、文化输出强、语音大幅简化"),
                    ("西班牙语", "火", "全球扩散、借词丰富、殖民融合"),
                    ("意大利语", "火", "文艺复兴输出、方言连续体"),
                    ("葡萄牙语", "火", "全球扩散、巴西变体、借词丰富"),
                    ("罗马尼亚语", "土", "巴尔干语言联盟、格系统残留"),
                    ("加泰罗尼亚语", "木", "区域扩张、语言复兴运动"),
                ]
            },
            "斯拉夫语族": {
                "wuxing": "土",
                "languages": [
                    ("俄语", "土", "格系统完整（6格），语法保守"),
                    ("波兰语", "金", "7格系统，鼻元音保持"),
                    ("捷克语", "金", "长/短元音对立，形态规则"),
                    ("乌克兰语", "土", "呼格保持，词汇保守"),
                    ("塞尔维亚-克罗地亚语", "火", "双字母系统（西里尔/拉丁），融合性强"),
                ]
            },
            "印度-伊朗语族": {
                "wuxing": "木",
                "languages": [
                    ("印地语", "木", "分支扩散，天城体文字"),
                    ("波斯语", "火", "丝绸之路借词，阿拉伯语影响"),
                    ("梵语", "金", "精密语法规则，八格系统"),
                    ("孟加拉语", "木", "东部分支，语音创新"),
                    ("普什图语", "金", "复杂格系统，形态丰富"),
                ]
            },
            "凯尔特语族": {
                "wuxing": "木",
                "languages": [
                    ("爱尔兰语", "土", "最古老白话文学，语法保守"),
                    ("威尔士语", "木", "语言复兴运动，分支创新"),
                    ("苏格兰盖尔语", "木", "区域扩张，濒危保护"),
                    ("布列塔尼语", "木", "大陆凯尔特残留，法语接触"),
                ]
            },
            "希腊语族": {
                "wuxing": "土",
                "languages": [
                    ("希腊语", "土", "3000年连续书写，语法极度保守"),
                ]
            },
            "波罗的语族": {
                "wuxing": "土",
                "languages": [
                    ("立陶宛语", "土", "最接近原始印欧语，格系统保守"),
                    ("拉脱维亚语", "水", "芬兰-乌戈尔语接触，声调创新"),
                ]
            },
        }
    },
    "汉藏语系": {
        "wuxing": "土",
        "depth": "L1",
        "subfamilies": {
            "汉语族": {
                "wuxing": "土",
                "languages": [
                    ("官话", "水", "声调简化至4声，适应性最强，通用语"),
                    ("粤语", "土", "入声保持，9声调，古汉语特征保守"),
                    ("闽语", "木", "上古汉语分支，白读/文读双层"),
                    ("吴语", "水", "浊音保持，连续变调复杂"),
                    ("客家话", "土", "迁徙保守，中古汉语特征保持"),
                    ("赣语", "水", "过渡方言，南北特征混合"),
                    ("湘语", "木", "古楚语底层，区域性创新"),
                ]
            },
            "藏缅语族": {
                "wuxing": "金",
                "languages": [
                    ("藏语", "金", "书面语千年不变，语法规则清晰"),
                    ("缅甸语", "火", "巴利语借词，南传佛教文化圈"),
                    ("彝语", "木", "独立音节文字，六大分支扩散"),
                    ("克伦语", "木", "SVO语序创新，偏离藏缅主流"),
                ]
            },
        }
    },
    "南岛语系": {
        "wuxing": "木",
        "depth": "L1",
        "subfamilies": {
            "马来-波利尼西亚语族": {
                "wuxing": "木",
                "languages": [
                    ("马来语", "火", "贸易通用语，借词丰富（梵/阿/英/荷）"),
                    ("印尼语", "火", "标准化马来语变体，融合性强"),
                    ("他加禄语", "木", "焦点系统创新，动词形态复杂"),
                    ("毛利语", "木", "波利尼西亚分支，语音简化"),
                    ("夏威夷语", "水", "极小音位系统（13个），极端简化"),
                    ("马达加斯加语", "木", "最远扩散，跨印度洋到达非洲"),
                    ("斐济语", "水", "美拉尼西亚接触，语音适应"),
                ]
            },
            "台湾南岛语族": {
                "wuxing": "水",
                "languages": [
                    ("阿美语", "木", "台湾最大南岛民族，分支扩散"),
                    ("泰雅语", "木", "古南岛语特征保持"),
                    ("排湾语", "金", "贵族语体分层，形态规则"),
                ]
            },
        }
    },
    "突厥语系": {
        "wuxing": "火",
        "depth": "L1",
        "subfamilies": {
            "乌古斯语族": {
                "wuxing": "火",
                "languages": [
                    ("土耳其语", "火", "拉丁化改革，借词替换，融合创新"),
                    ("阿塞拜疆语", "火", "波斯/俄语接触，多重借词层"),
                    ("土库曼语", "土", "元音和谐严格，语法保守"),
                ]
            },
            "葛逻禄语族": {
                "wuxing": "土",
                "languages": [
                    ("乌兹别克语", "土", "无元音和谐简化，阿拉伯字母→拉丁→西里尔"),
                    ("维吾尔语", "火", "丝绸之路借词，多元文化接触"),
                ]
            },
            "钦察语族": {
                "wuxing": "木",
                "languages": [
                    ("哈萨克语", "木", "草原扩散，从西里尔→拉丁转型"),
                    ("吉尔吉斯语", "土", "长元音保持，语法保守"),
                    ("鞑靼语", "火", "俄语深度接触，借词层叠"),
                ]
            },
        }
    },
    "亚非语系": {
        "wuxing": "金",
        "depth": "L1",
        "subfamilies": {
            "闪米特语族": {
                "wuxing": "金",
                "languages": [
                    ("阿拉伯语", "火", "古兰经标准语，方言连续体，借词输出"),
                    ("希伯来语", "金", "唯一成功复兴的古典语言"),
                    ("阿姆哈拉语", "土", "埃塞俄比亚官方语，吉兹字母保持"),
                    ("阿拉姆语", "土", "近东通用语3000年，今仅存小社区"),
                ]
            },
            "柏柏尔语族": {
                "wuxing": "木",
                "languages": [
                    ("塔马齐格特语", "木", "北非原住民语言，提非纳字母复活"),
                    ("卡比尔语", "木", "阿尔及利亚最大柏柏尔语，法语接触"),
                ]
            },
            "埃及语族": {
                "wuxing": "土",
                "languages": [
                    ("科普特语", "土", "古埃及语最后阶段，礼仪语存活"),
                ]
            },
            "库施特语族": {
                "wuxing": "木",
                "languages": [
                    ("索马里语", "木", "非洲之角扩散，声调创新"),
                    ("奥罗莫语", "木", "埃塞俄比亚最多人口母语，分支扩张"),
                ]
            },
        }
    },
}

# 借词关系（跨语系/语族）
BORROW_EDGES = [
    # 诺曼征服：英语 ← 法语（诺曼法语）
    ("英语", "法语", "诺曼征服（1066），词汇双源分层"),
    # 拉丁语 → 罗曼语族全体（拉丁化）
    ("意大利语", "拉丁语", "直系后代"),
    ("法语", "拉丁语", "通俗拉丁语后代"),
    ("西班牙语", "拉丁语", "通俗拉丁语后代"),
    # 丝绸之路：波斯语 ↔ 阿拉伯语
    ("波斯语", "阿拉伯语", "伊斯兰征服后大量借词"),
    ("土耳其语", "阿拉伯语", "奥斯曼时期借词（后部分替换）"),
    ("土耳其语", "波斯语", "奥斯曼文学语言借词"),
    # 梵语 → 东南亚
    ("马来语", "梵语", "印度化时期借词"),
    ("印尼语", "梵语", "印度化时期借词"),
    # 英语 → 全球（现代借词）
    ("日语", "英语", "现代借词（非本数据集节点，预留）"),
    # 汉语 → 东亚
    ("日语", "汉语", "汉字词借入（非本数据集节点，预留）"),
    ("韩语", "汉语", "汉字词借入（非本数据集节点，预留）"),
    ("越南语", "汉语", "汉越词（非本数据集节点，预留）"),
]

# 同源关系（同一语族内的紧密同源）
COGNATE_GROUPS = [
    # 日耳曼语族内部（西日耳曼支）
    ["英语", "德语", "荷兰语"],
    # 北日耳曼支
    ["瑞典语", "挪威语", "丹麦语", "冰岛语"],
    # 罗曼语族内部
    ["法语", "西班牙语", "意大利语", "葡萄牙语"],
    # 斯拉夫语族内部
    ["俄语", "乌克兰语", "波兰语", "捷克语"],
    # 印度-伊朗语族内部
    ["印地语", "孟加拉语", "梵语"],
    # 突厥语族内部
    ["土耳其语", "阿塞拜疆语", "土库曼语"],
    # 闪米特语族内部
    ["阿拉伯语", "希伯来语", "阿拉姆语"],
    # 汉语族内部
    ["官话", "粤语", "闽语", "吴语", "客家话"],
]


def build_language_tree():
    """构建语言谱系树数据集"""
    nodes = []
    edges = []
    node_id = 0
    name_to_id = {}  # 名称→ID 映射

    def add_node(name, level, parent_id, category, wuxing, cognitive_depth, note=""):
        nonlocal node_id
        node_id += 1
        nid = f"lang_{node_id:04d}"
        nodes.append({
            "id": nid,
            "name": name,
            "level": level,
            "parent_id": parent_id,
            "category": category,
            "wuxing": wuxing,
            "cognitive_depth": cognitive_depth,
            "position": None,
            "note": note,
        })
        name_to_id[name] = nid
        return nid

    def add_edge(src, tgt, relation):
        edges.append({
            "source_id": src,
            "target_id": tgt,
            "relation": relation,
        })

    # 添加根节点
    root_id = add_node("人类语言", 0, None, "root", "土", "L1", "全球语言谱系树根节点")

    # 构建语系
    for family_name, family_info in LANGUAGE_TREE.items():
        family_id = add_node(
            family_name, 1, root_id, "root",
            family_info["wuxing"], family_info["depth"],
            f"语系"
        )
        add_edge(root_id, family_id, "parent_of")

        # 构建语族
        for subfamily_name, subfamily_info in family_info["subfamilies"].items():
            subfamily_id = add_node(
                subfamily_name, 2, family_id, family_name,
                subfamily_info["wuxing"], "L2",
                f"{family_name} → {subfamily_name}"
            )
            add_edge(family_id, subfamily_id, "parent_of")

            # 构建语言
            for lang_name, lang_wx, lang_note in subfamily_info["languages"]:
                lang_id = add_node(
                    lang_name, 3, subfamily_id, subfamily_name,
                    lang_wx, "L3", lang_note
                )
                add_edge(subfamily_id, lang_id, "parent_of")

    # 添加借词关系边
    for src_name, tgt_name, note in BORROW_EDGES:
        if src_name in name_to_id and tgt_name in name_to_id:
            add_edge(name_to_id[src_name], name_to_id[tgt_name], "borrows_from")
        # 如果目标不在数据集中，跳过（如日语、韩语、越南语、拉丁语）

    # 添加同源关系边
    for group in COGNATE_GROUPS:
        ids_in_group = [name_to_id[n] for n in group if n in name_to_id]
        for i in range(len(ids_in_group)):
            for j in range(i + 1, len(ids_in_group)):
                add_edge(ids_in_group[i], ids_in_group[j], "cognate_with")

    snapshot = {
        "collect_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "source": "language_family_tree",
        "schema": "compatible_with_baai_snapshot",
        "method": "manual_curation",
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "total_families": len(LANGUAGE_TREE),
            "total_subfamilies": sum(len(f["subfamilies"]) for f in LANGUAGE_TREE.values()),
            "total_languages": sum(
                sum(len(s["languages"]) for s in f["subfamilies"].values())
                for f in LANGUAGE_TREE.values()
            ),
            "family_names": list(LANGUAGE_TREE.keys()),
            "wuxing_mapping": "语言领域特化：木=扩张/分支/创新，火=交互/融合/借词，土=稳定/保守/连续，金=规则/形态/边界，水=适应/变体/吸收",
        }
    }

    return snapshot


def main():
    snapshot = build_language_tree()
    meta = snapshot["metadata"]

    print("=" * 60)
    print("语言谱系树数据集构建")
    print("=" * 60)
    print(f"  语系: {meta['total_families']} 个")
    print(f"  语族: {meta['total_subfamilies']} 个")
    print(f"  语言: {meta['total_languages']} 个")
    print(f"  节点总数: {len(snapshot['nodes'])}")
    print(f"  边总数: {len(snapshot['edges'])}")

    # 统计边类型
    from collections import Counter
    edge_types = Counter(e["relation"] for e in snapshot["edges"])
    print(f"\n  边类型分布:")
    for rel, count in edge_types.most_common():
        print(f"    {rel}: {count}")

    # 统计五行分布
    wx_dist = Counter(n["wuxing"] for n in snapshot["nodes"] if n["level"] > 0)
    print(f"\n  五行分布（L1-L3节点）:")
    for wx in ["木", "火", "土", "金", "水"]:
        cnt = wx_dist.get(wx, 0)
        total = sum(wx_dist.values())
        print(f"    {wx}: {cnt} ({cnt/total*100:.1f}%)")

    # 统计认知深度分布
    depth_dist = Counter(n["cognitive_depth"] for n in snapshot["nodes"])
    print(f"\n  认知深度分布:")
    for d in ["L1", "L2", "L3"]:
        print(f"    {d}: {depth_dist.get(d, 0)}")

    # 保存
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "language_tree"
    )
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "language_tree_snapshot.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    print(f"\n  已保存: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()