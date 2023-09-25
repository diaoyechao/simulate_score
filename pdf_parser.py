import os

import pdfplumber

from rules import *
from utils import *

with pdfplumber.open("data/type_0/综合交通换乘中心全过程设计.pdf") as pdf:
    bid_rejection_rule = get_bid_rejection_rule_pdf(pdf)
    bid_rejection_rules = [item for item in re.split("\\d+、", bid_rejection_rule)][1:]
    print("@0.废标规则：", bid_rejection_rules)
    print("------")
    start, end = get_chapter_start_end_position(pdf)
    print("")
    print(f"@1.评标办法章节开始位置{start}，结束位置{end}。")
    print("------")
    evaluation_method = judge_evaluation_method_pdf(start, end, pdf)
    if not evaluation_method:
        print("不是综合评估法或综合评分法。")
        exit()
    filtered_split_rating_sub_items = get_rating_sub_items(start, end, pdf)
    filtered_split_rating_sub_items = [filtered_split_rating_sub_item for filtered_split_rating_sub_item in
                                       filtered_split_rating_sub_items if len(filtered_split_rating_sub_item) > 10]

print("")
print("@2.评分子项内容")
for filtered_split_rating_sub_item in filtered_split_rating_sub_items:
    print(filtered_split_rating_sub_item)
    print("******")
print("------")

print("")
fixed_score_items = []
subject_score_items = []

if os.path.exists("result.txt"):
    os.remove("result.txt")
w = open("./result.txt", "a", encoding="utf-8")

for sub_item in filtered_split_rating_sub_items:
    # 可计算得分项
    # 判断评分子项对应的规则
    filter_pattern = get_rating_sub_items_filter_patterns()
    if not re.search(filter_pattern, sub_item):
        subject_score_items.append(sub_item)
        continue
    w.write(sub_item + "\n")
    print(sub_item)
    rule = recognize_rule(sub_item)
    w.write(str(rule) + "\n")
    w.write("\n")
    print(rule)
    print("&&&&&&")
    if rule:
        if rule[0] == "rule1":
            rule1_fixed_score_items = rule1(sub_item)
            fixed_score_items.append(rule1_fixed_score_items)
        if rule[0] == "rule2":
            rule2_fixed_score_items = rule2(sub_item)
            fixed_score_items.append(rule2_fixed_score_items)
        elif rule[0] == "rule3":
            rule3_fixed_score_items = rule3(sub_item)
            fixed_score_items.append(rule3_fixed_score_items)
    else:
        subject_score_items.append(sub_item)

print("")
print("@3.可计算得分项内容及其对应规则")
fixedScoreResp = []
for fixed_score_item in fixed_score_items:
    fixedScoreResp.append(fixed_score_item)
    print(fixed_score_item)
    print("******")
print("")

print("@4.主观得分项及其对应最大分值")
subjectiveScoreResp = []
for subject_score_item in subject_score_items:
    subject_score_item_dict = {
        "scoreItem": subject_score_item,
        "maxScore": None,
        "scoreType": 2,
        "defaultScore": None
    }
    max_score_pattern = "最多得\\d+分|最高得(\\d+)分|满分\\d+分|最高不超过(\\d+)分|得\\d+分|得\\d+(\\.\\d+)?分" \
                        "|得\\d+(\\.\\d+)?～\\d+分|得\\d+(\\.\\d+)?～\\d+(\\.\\d+)?分|为\\d+分|得\\d+-\\d+分|加\\d+分"
    max_score_iter = re.finditer(max_score_pattern, subject_score_item)
    scores = [max_score.group() for item in max_score_iter for max_score in
              re.finditer("\\d+(\\.\\d+)?|\\d+", item.group())]

    scores = [int(score) if isinstance(is_integer_or_float(score), int) else float(score) for score in scores]
    if scores:
        subject_score_item_dict["maxScore"] = max(scores)
    subjectiveScoreResp.append(subject_score_item_dict)
print(subjectiveScoreResp)

businessScoreResp = {
    "businessScoreItem": 30,
    "controlPrice": 0.0,
    "upRuleRate": None,
    "downRuleRate": None,
    "basicRate": None,
    "basicPrice": None
}
