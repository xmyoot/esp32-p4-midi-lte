"""Search JLCPCB assembly parts library. usage: python jlc_search.py "query" ["query2" ...] [-n 5]"""
import json, sys, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"

def search(q, n=5):
    body = json.dumps({"keyword": q, "currentPage": 1, "pageSize": n}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    return (d.get("data") or {}).get("componentPageInfo", {}).get("list") or []

if __name__ == "__main__":
    args = sys.argv[1:]; n = 5
    if "-n" in args: i = args.index("-n"); n = int(args[i+1]); del args[i:i+2]
    for q in args:
        print(f"=== {q}")
        for c in search(q, n):
            p = (c.get("componentPrices") or [{}])[0].get("productPrice")
            lib = {"base": "BASIC", "expand": "ext"}.get(c.get("componentLibraryType"), c.get("componentLibraryType"))
            if c.get("preferredComponentFlag"): lib += "/pref"
            print(f"  {c.get('componentCode'):>10} {str(c.get('componentModelEn'))[:28]:28} {str(c.get('componentSpecificationEn'))[:16]:16} {lib:10} stk={c.get('stockCount'):>8} ${p}  {str(c.get('describe'))[:70]}")
        time.sleep(0.4)
