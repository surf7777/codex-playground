import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime

url = "https://www.release.tdnet.info/inbs/I_main_00.html"

today = datetime.now().strftime("%Y%m%d")
filename = f"tdnet_{today}.tsv"

print("TDnet取得中...")

response = requests.get(url)
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.text, "html.parser")

rows = []
for tr in soup.find_all("tr"):
    cols = tr.find_all("td")
    if len(cols) >= 4:
        row = [col.get_text(strip=True) for col in cols]
        rows.append(row)

print(f"取得件数: {len(rows)}")

with open(filename, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter="\t")
    writer.writerows(rows)

print(f"{filename} 保存完了")
