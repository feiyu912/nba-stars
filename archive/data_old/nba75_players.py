"""
NBA 75th Anniversary Team (76 players) - ID 查询 + 数据覆盖评估
"""
from nba_api.stats.static import players as nba_players
import time

NBA75 = [
    "Kareem Abdul-Jabbar", "Ray Allen", "Giannis Antetokounmpo", "Carmelo Anthony",
    "Nate Archibald", "Paul Arizin", "Charles Barkley", "Rick Barry",
    "Elgin Baylor", "Dave Bing", "Larry Bird", "Kobe Bryant",
    "Wilt Chamberlain", "Bob Cousy", "Dave Cowens", "Billy Cunningham",
    "Stephen Curry", "Anthony Davis", "Dave DeBusschere", "Clyde Drexler",
    "Tim Duncan", "Kevin Durant", "Julius Erving", "Patrick Ewing",
    "Walt Frazier", "Kevin Garnett", "George Gervin", "Hal Greer",
    "James Harden", "John Havlicek", "Elvin Hayes", "Allen Iverson",
    "LeBron James", "Magic Johnson", "Sam Jones", "Michael Jordan",
    "Jason Kidd", "Kawhi Leonard", "Damian Lillard", "Jerry Lucas",
    "Karl Malone", "Moses Malone", "Pete Maravich", "Bob McAdoo",
    "Kevin McHale", "George Mikan", "Reggie Miller", "Earl Monroe",
    "Steve Nash", "Dirk Nowitzki", "Hakeem Olajuwon", "Shaquille O'Neal",
    "Robert Parish", "Chris Paul", "Gary Payton", "Bob Pettit",
    "Paul Pierce", "Scottie Pippen", "Willis Reed", "Oscar Robertson",
    "David Robinson", "Dennis Rodman", "Bill Russell", "Dolph Schayes",
    "Bill Sharman", "John Stockton", "Isiah Thomas", "Nate Thurmond",
    "Wes Unseld", "Dwyane Wade", "Bill Walton", "Jerry West",
    "Russell Westbrook", "Lenny Wilkens", "Dominique Wilkins", "James Worthy",
]

# 加上东契奇 (未入选75大但在我们的原始分析中)
NBA75_PLUS = NBA75 + ["Luka Doncic"]

found = []
not_found = []

for name in NBA75_PLUS:
    results = nba_players.find_players_by_full_name(name)
    if results:
        p = results[0]
        found.append({
            "name": name,
            "nba_id": p["id"],
            "active": p["is_active"],
        })
    else:
        # 尝试模糊匹配
        parts = name.split()
        last = parts[-1]
        by_last = nba_players.find_players_by_last_name(last)
        matches = [p for p in by_last if parts[0].lower() in p["first_name"].lower()]
        if matches:
            p = matches[0]
            found.append({
                "name": name,
                "nba_id": p["id"],
                "active": p["is_active"],
            })
        else:
            not_found.append(name)

print(f"Found: {len(found)}/{len(NBA75_PLUS)}")
print(f"Not found: {not_found}")
print()

# 保存
import json
with open("data/nba75_ids.json", "w") as f:
    json.dump(found, f, indent=2)

print(f"Saved to data/nba75_ids.json")

# 按时代分类
for p in found:
    print(f"  {p['nba_id']:>10d}  {'ACTIVE' if p['active'] else '      '}  {p['name']}")
