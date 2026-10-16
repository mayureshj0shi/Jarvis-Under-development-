import re
import requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def fetch_url(url, max_chars=4000):
    try:
        r = requests.get(url, headers=_HEADERS, timeout=20)
        r.raise_for_status()
        text = re.sub(r"<script.*?</script>", "", r.text, flags=re.S)
        text = re.sub(r"<style.*?</style>", "", text, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return {"url": url, "status": r.status_code, "text": text[:max_chars]}
    except Exception as e:
        return {"error": str(e)}


def web_search(query, max_results=5):
    try:
        from urllib.parse import unquote, urlparse, parse_qs

        r = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=_HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        results = []
        for m in re.finditer(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S
        ):
            href = m.group(1)
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            url = href
            if "/l/?" in href or "uddg=" in href:
                q = parse_qs(urlparse(href).query)
                if "uddg" in q:
                    url = unquote(q["uddg"][0])
            results.append({"title": title, "url": url})
            if len(results) >= max_results:
                break
        return {"query": query, "results": results}
    except Exception as e:
        return {"error": str(e)}
