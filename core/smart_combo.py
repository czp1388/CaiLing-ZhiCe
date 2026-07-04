#!/usr/bin/env python3
"""聪明组合生成器（旋转矩阵）"""
import json, sys
ROTATION_10 = [
    [1,2,3,4,5,6],[1,2,3,7,8,9],[1,2,4,7,9,10],[1,2,5,8,9,10],
    [1,3,4,6,7,9],[1,3,5,6,8,10],[1,4,5,6,7,8],[1,4,6,8,9,10],
    [1,5,7,8,9,10],[2,3,4,5,7,10],[2,3,4,6,8,10],[2,3,5,6,7,8],
    [2,4,5,6,9,10],[2,6,7,8,9,10],[3,4,5,7,9,10],[3,4,6,7,8,9],
]
def generate(nums):
    n = len(nums)
    if n == 10:
        combos = [[nums[i-1] for i in idxs] for idxs in ROTATION_10]
        return {"nums": nums, "combos": combos, "count": 16, "desc": "10个号16注中6保5"}
    return {"error": f"不支持{n}个号"}
if __name__ == "__main__":
    nums = list(map(int, sys.argv[1:])) if len(sys.argv) > 1 else list(range(1,11))
    print(json.dumps(generate(nums), ensure_ascii=False, indent=2))
