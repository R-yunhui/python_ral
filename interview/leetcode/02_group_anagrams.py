from typing import List


class Solution:

    def groupAnagrams(self, strs: List[str]) -> List[List[str]]:
        hash_map: dict[str, List[str]] = {}
        for str in strs:
            sorted_str = "".join(sorted(str))
            list = hash_map.get(sorted_str, [])
            list.append(str)
            hash_map[sorted_str] = list

        return [value for value in hash_map.values()]


if __name__ == "__main__":
    solution = Solution()
    print(solution.groupAnagrams(["eat", "tea", "tan", "ate", "nat", "bat"]))
