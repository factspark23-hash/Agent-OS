#!/usr/bin/env python3
"""
Agent-OS Stress Test: Browse 50 websites including bot-protected ones.
Tests anti-detection, content extraction, and real browsing capability.
"""
import httpx
import json
import time
import sys

TOKEN = "agent-os-main-2026"
BASE = "http://127.0.0.1:8001"

# 50 websites — mix of normal + bot-protected + heavy anti-bot
SITES = [
    # Easy sites (baseline)
    ("https://example.com", "Example Domain"),
    ("https://httpbin.org", "httpbin"),
    ("https://www.wikipedia.org", "Wikipedia"),
    ("https://news.ycombinator.com", "Hacker News"),
    ("https://github.com", "GitHub"),
    ("https://stackoverflow.com", "Stack Overflow"),
    
    # E-commerce (heavy bot detection)
    ("https://www.amazon.com", "Amazon"),
    ("https://www.ebay.com", "eBay"),
    ("https://www.walmart.com", "Walmart"),
    ("https://www.bestbuy.com", "Best Buy"),
    ("https://www.target.com", "Target"),
    
    # Social media (aggressive anti-bot)
    ("https://www.reddit.com", "Reddit"),
    ("https://twitter.com", "X/Twitter"),
    ("https://www.linkedin.com", "LinkedIn"),
    ("https://www.instagram.com", "Instagram"),
    ("https://www.facebook.com", "Facebook"),
    
    # News sites (often Cloudflare/Imperva)
    ("https://www.nytimes.com", "NY Times"),
    ("https://www.cnn.com", "CNN"),
    ("https://www.bbc.com", "BBC"),
    ("https://www.reuters.com", "Reuters"),
    ("https://www.theguardian.com", "The Guardian"),
    ("https://www.washingtonpost.com", "Washington Post"),
    
    # Travel (aggressive bot protection)
    ("https://www.booking.com", "Booking.com"),
    ("https://www.expedia.com", "Expedia"),
    ("https://www.tripadvisor.com", "TripAdvisor"),
    ("https://www.skyscanner.com", "Skyscanner"),
    
    # Search engines & portals
    ("https://www.google.com", "Google"),
    ("https://www.bing.com", "Bing"),
    ("https://duckduckgo.com", "DuckDuckGo"),
    
    # Finance (heavy security)
    ("https://www.bloomberg.com", "Bloomberg"),
    ("https://finance.yahoo.com", "Yahoo Finance"),
    ("https://www.investing.com", "Investing.com"),
    ("https://www.coinmarketcap.com", "CoinMarketCap"),
    
    # Tech companies
    ("https://www.microsoft.com", "Microsoft"),
    ("https://www.apple.com", "Apple"),
    ("https://www.google.com/about", "Google About"),
    ("https://www.cloudflare.com", "Cloudflare"),
    
    # Government & edu (various protections)
    ("https://www.nasa.gov", "NASA"),
    ("https://www.nih.gov", "NIH"),
    ("https://www.whitehouse.gov", "White House"),
    
    # Heavy Cloudflare / bot detection sites
    ("https://www.cloudflare.com", "Cloudflare Main"),
    ("https://www.zillow.com", "Zillow"),
    ("https://www.craigslist.org", "Craigslist"),
    ("https://www.glassdoor.com", "Glassdoor"),
    
    # Streaming (heavy DRM/bot protection)
    ("https://www.imdb.com", "IMDb"),
    ("https://www.rottentomatoes.com", "Rotten Tomatoes"),
    
    # Miscellaneous
    ("https://www.etsy.com", "Etsy"),
    ("https://www.paypal.com", "PayPal"),
    ("https://www.medium.com", "Medium"),
    ("https://dev.to", "Dev.to"),
    ("https://www.producthunt.com", "Product Hunt"),
]

def cmd(command, **kwargs):
    """Send command to Agent-OS."""
    payload = {"token": TOKEN, "command": command, **kwargs}
    r = httpx.post(f"{BASE}/command", json=payload, timeout=45)
    return r.json()

results = []
success = 0
failed = 0
blocked = 0

print(f"\n{'='*70}")
print(f"  🤖 AGENT-OS STRESS TEST — 50 WEBSITES")
print(f"  Including bot-protected, Cloudflare, anti-scrape sites")
print(f"{'='*70}\n")

for i, (url, name) in enumerate(SITES, 1):
    sys.stdout.write(f"\r[{i:2d}/50] Testing {name:<25s}")
    sys.stdout.flush()
    
    start = time.time()
    try:
        # Navigate
        nav = cmd("navigate", url=url)
        elapsed = round(time.time() - start, 1)
        
        if nav.get("status") == "success":
            title = nav.get("title", "?")
            status_code = nav.get("status_code", 0)
            blocked_reqs = nav.get("blocked_requests", 0)
            
            # Get content
            content = cmd("get-content")
            text = content.get("text", "")[:150].replace("\n", " ").strip()
            
            # Determine if we got real content or a block page
            is_blocked = False
            block_indicators = ["access denied", "captcha", "bot detected", "just a moment", 
                              "checking your browser", "cloudflare", "please verify", "unusual traffic"]
            for indicator in block_indicators:
                if indicator in title.lower() or indicator in text.lower():
                    is_blocked = True
                    break
            
            if is_blocked:
                blocked += 1
                status = "🛡️ BLOCKED"
            else:
                success += 1
                status = "✅ OK"
            
            results.append({
                "i": i, "name": name, "url": url, "status": status,
                "title": title[:50], "text": text[:80], "time": elapsed,
                "code": status_code, "blocked_reqs": blocked_reqs
            })
        else:
            failed += 1
            error = nav.get("error", "unknown")[:40]
            results.append({
                "i": i, "name": name, "url": url, "status": "❌ FAIL",
                "title": error, "text": "", "time": elapsed,
                "code": 0, "blocked_reqs": 0
            })
    except Exception as e:
        failed += 1
        elapsed = round(time.time() - start, 1)
        results.append({
            "i": i, "name": name, "url": url, "status": "❌ ERROR",
            "title": str(e)[:50], "text": "", "time": elapsed,
            "code": 0, "blocked_reqs": 0
        })

# Print results
print(f"\n\n{'='*70}")
print(f"  RESULTS")
print(f"{'='*70}\n")
print(f"{'#':>3} {'Status':<10} {'Name':<20} {'Time':>5}s  {'Title':<45}")
print(f"{'─'*3} {'─'*10} {'─'*20} {'─'*5}  {'─'*45}")

for r in results:
    print(f"{r['i']:>3} {r['status']:<10} {r['name']:<20} {r['time']:>5.1f}  {r['title'][:45]}")

print(f"\n{'='*70}")
print(f"  SUMMARY")
print(f"{'='*70}")
print(f"  ✅ Success:  {success}/50  ({success/50*100:.0f}%)")
print(f"  🛡️ Blocked:  {blocked}/50  ({blocked/50*100:.0f}%)")
print(f"  ❌ Failed:   {failed}/50  ({failed/50*100:.0f}%)")
print(f"  🌐 Total:    {success + blocked + failed}/50")
print(f"{'='*70}\n")

# Save detailed results
with open("/root/.openclaw/workspace/Agent-OS/stress_test_results.json", "w") as f:
    json.dump({"summary": {"success": success, "blocked": blocked, "failed": failed, "total": 50}, "results": results}, f, indent=2)

print("📁 Detailed results saved to stress_test_results.json")
