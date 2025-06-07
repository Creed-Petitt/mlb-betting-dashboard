import requests

team_ids = [
    108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
    118, 119, 120, 121, 133, 134, 135, 136, 137, 138,
    139, 140, 141, 142, 143, 144, 145, 146, 147, 158
]

for tid in team_ids:
    url = f"https://www.mlbstatic.com/team-logos/{tid}.svg"
    r = requests.get(url)
    if r.status_code == 200:
        with open(f"static/team_logos/{tid}.svg", "wb") as f:
            f.write(r.content)
    else:
        print(f"Failed for team ID {tid}")
