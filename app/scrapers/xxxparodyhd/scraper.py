from __future__ import annotations

import json
import re
import os
import random
import string
import time
from typing import Any, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.core import pool


def can_handle(host: str) -> bool:
    return "xxxparodyhd.net" in host.lower()


async def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = await pool.client.get(url, headers=headers, follow_redirects=True)
    resp.raise_for_status()
    
    # Check if a paginated request was redirected to the base URL (meaning no more pages)
    if "/page/" in url and "/page/" not in str(resp.url):
        return ""
        
    return resp.text


def _text(el: Any) -> Optional[str]:
    if el is None:
        return None
    t = getattr(el, "get_text", None)
    if callable(t):
        return t(strip=True) or None
    return None


def _best_image_url(img: Any) -> Optional[str]:
    if img is None:
        return None
    for k in ("data-src", "data-original", "data-lazy", "src"):
        v = img.get(k)
        if v and str(v).strip():
            url = str(v).strip()
            if url.startswith("//"):
                return f"https:{url}"
            return url
    return None


async def resolve_dood(embed_url: str) -> Optional[tuple[str, str]]:
    try:
        parsed = urlparse(embed_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Referer": "https://xxxparodyhd.net/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "iframe",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Upgrade-Insecure-Requests": "1",
        }
        
        resp = await pool.client.get(embed_url, headers=headers, follow_redirects=True)
        if resp.status_code != 200:
            return None
        
        html = resp.text
        pass_match = re.search(r"['\"]/pass_md5/([^'\"]+)['\"]", html)
        if not pass_match:
            return None
            
        pass_path = pass_match.group(1)
        pass_url = f"{base_url}/pass_md5/{pass_path}"
        
        pass_headers = {
            "User-Agent": headers["User-Agent"],
            "Referer": str(resp.url),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        
        pass_resp = await pool.client.get(pass_url, headers=pass_headers)
        if pass_resp.status_code != 200:
            return None
            
        base_cdn = pass_resp.text
        
        rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        token = pass_path.split('/')[-1]
        expiry = int(time.time() * 1000)
        
        direct_url = f"{base_cdn}{rand_str}?token={token}&expiry={expiry}"
        return direct_url, str(resp.url)
    except Exception:
        return None


async def resolve_voe(embed_url: str) -> Optional[tuple[str, str]]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Referer": "https://xxxparodyhd.net/",
        }
        
        resp = await pool.client.get(embed_url, headers=headers, follow_redirects=True)
        if resp.status_code != 200:
            return None
            
        html = resp.text
        
        js_redirect = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", html)
        if js_redirect:
            redirect_url = js_redirect.group(1)
            if redirect_url.startswith("//"):
                redirect_url = f"https:{redirect_url}"
            elif not redirect_url.startswith("http"):
                parsed = urlparse(str(resp.url))
                redirect_url = f"{parsed.scheme}://{parsed.netloc}{redirect_url}"
                
            headers["Referer"] = str(resp.url)
            resp = await pool.client.get(redirect_url, headers=headers, follow_redirects=True)
            if resp.status_code != 200:
                return None
            html = resp.text

        m3u8_match = re.search(r"['\"](https?://[^'\"\s]+\.m3u8[^'\"\s]*)['\"]", html)
        if m3u8_match:
            return m3u8_match.group(1), str(resp.url)
            
        base64_sources = re.search(r"sources['\"]?\s*:\s*['\"]([a-zA-Z0-9+/=]{50,})['\"]", html)
        if not base64_sources:
             base64_sources = re.search(r"['\"]sources['\"]\s*:\s*\[\s*['\"]([^'\"]+)['\"]", html)
             
        if base64_sources:
             import base64
             try:
                 decoded = base64.b64decode(base64_sources.group(1)).decode('utf-8', errors='ignore')
                 m3u8_match = re.search(r"['\"](https?://[^'\"\s]+\.m3u8[^'\"\s]*)['\"]", decoded)
                 if m3u8_match:
                     return m3u8_match.group(1), str(resp.url)
             except Exception:
                 pass
        
        return None
    except Exception:
        return None


async def resolve_mixdrop(embed_url: str) -> Optional[tuple[str, str]]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Referer": "https://xxxparodyhd.net/",
        }
        
        resp = await pool.client.get(embed_url, headers=headers, follow_redirects=True)
        if resp.status_code != 200:
            return None
            
        html = resp.text
        # Look for MDCore.wurl or similar in the HTML
        wurl_match = re.search(r"MDCore\.wurl\s*=\s*['\"]([^'\"]+)['\"]", html)
        if wurl_match:
            wurl = wurl_match.group(1)
            if wurl.startswith("//"):
                wurl = f"https:{wurl}"
            return wurl, str(resp.url)
            
        # If not found, it might be in a packed script
        # 0.11="//3.4.2/..."
        packed_match = re.search(r"eval\(function\(p,a,c,k,e,d\).+?['\"]\.split\(", html)
        if packed_match:
            # Extract word list
            k_match = re.search(r"['\"]([^'\"]+)['\"]\s*\.split\s*\(\s*['\"]\|['\"]\s*\)", html)
            if k_match:
                words = k_match.group(1).split('|')
                # Find the template string
                # Usually it starts with 0.Something or contains //
                template_match = re.search(r"['\"]([^'\"]*//[^'\"]+)['\"]", html)
                if template_match:
                    template = template_match.group(1)
                    # Reconstruct the URL by replacing indices
                    # This is complex to do right with regex, but we can try common indices
                    def replace_func(match):
                        idx = int(match.group(0))
                        if idx < len(words) and words[idx]:
                            return words[idx]
                        return match.group(0)
                        
                    url = re.sub(r"\b\d+\b", replace_func, template)
                    if url.startswith("//"):
                        url = f"https:{url}"
                    if "http" in url:
                        return url.replace(" ", ""), str(resp.url)

        # Fallback: look for any .mp4 link in the words list if packed
        if packed_match and k_match:
             for word in words:
                 if 'mp4' in word and word.startswith('http'):
                     return word, str(resp.url)

        # Final Fallback: look for any MP4 link
        mp4_match = re.search(r"['\"](https?://[^'\"\s]+\.mp4[^'\"\s]*)['\"]", html)
        if mp4_match:
            return mp4_match.group(1), str(resp.url)
            
        return None
    except Exception:
        return None


async def resolve_embed(embed_url: str) -> Optional[tuple[str, str]]:
    try:
        parsed = urlparse(embed_url)
        host = parsed.netloc.lower()
        
        if any(h in host for h in ("dood", "doply", "myvidplay", "ds2play")):
            return await resolve_dood(embed_url)
        
        if "voe" in host:
            return await resolve_voe(embed_url)
        
        if "mixdrop" in host:
            return await resolve_mixdrop(embed_url)
        
        return None
    except Exception:
        return None


async def parse_page(html: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")

    # Title
    title_node = soup.select_one("h1.entry-title, h1.post-title, h1")
    title = _text(title_node) or _text(soup.find("title")) or "Unknown Video"

    # Clean title
    for suffix in (" - XXXParodyHD", " – XXXParodyHD", " | XXXParodyHD"):
        if title.endswith(suffix):
            title = title[: -len(suffix)]

    # Description / meta
    desc_node = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
    description = desc_node.get("content") if desc_node else None

    # Thumbnail (og:image)
    og_img = soup.find("meta", property="og:image")
    thumbnail = og_img.get("content") if og_img else None

    # Extract embedded player URLs (iframes)
    embed_urls = []
    # Look for any a[href] tag containing an embed link
    for a_tag in soup.select("a[href]"):
        href = a_tag.get("href", "")
        text = _text(a_tag) or ""
        # Common embed hosts
        embed_hosts = ["dood", "doply", "vidnest", "player4me", "upns", "voe.sx",
                       "embedseek", "seekplayer", "mixdrop", "easyvidplayer", "rpmplay"]
        if any(h in href.lower() for h in embed_hosts) and 'xxxparodyhd.net' not in href.lower():
            # Avoid duplicates
            if not any(e["url"] == href for e in embed_urls):
                embed_urls.append({
                    "url": href,
                    "label": text or "Player",
                })

    # Also check for iframes
    for iframe in soup.select("iframe[src]"):
        src = iframe.get("src", "")
        if src and ("http" in src or src.startswith("//")):
            if src.startswith("//"):
                src = f"https:{src}"
            embed_urls.append({
                "url": src,
                "label": "Embedded Player",
            })

    # Build video data
    # XXXParodyHD doesn't host videos directly - it links to external embed players
    video_url = None
    streams = []
    
    # Try to resolve embeds to direct streams
    if embed_urls:
        for idx, embed in enumerate(embed_urls):
            resolved = await resolve_embed(embed["url"])
            if resolved:
                direct_url, referer = resolved
                streams.append({
                    "url": direct_url,
                    "quality": embed.get("label", f"Player {idx + 1}"),
                    "format": "hls" if ".m3u8" in direct_url else "mp4",
                    "referer": referer
                })
                if video_url is None:
                    video_url = direct_url
            else:
                # Fallback to embed if resolution failed or not supported
                streams.append({
                    "url": embed["url"],
                    "quality": embed.get("label", f"Player {idx + 1}"),
                    "format": "embed",
                })
        
        if video_url is None and streams:
            video_url = streams[0]["url"]

    # Tags / Genres
    tags = []
    for a in soup.select('.entry-terms a[href*="/genre/"], .tag-links a, a[rel="tag"]'):
        t = _text(a)
        if t:
            tags.append(t)

    # Category info
    category_links = soup.select('.entry-terms a[href*="/category/"]')
    categories = [_text(cl) for cl in category_links if _text(cl)]

    # Studio / Director
    studio_links = soup.select('.entry-terms a[href*="/director/"]')
    studio = _text(studio_links[0]) if studio_links else None

    # Cast
    cast_links = soup.select('.entry-terms a[href*="/cast/"]')
    cast = [_text(cl) for cl in cast_links if _text(cl)]

    # Year
    year_links = soup.select('.entry-terms a[href*="/release-year/"]')
    year = _text(year_links[0]) if year_links else None

    # Views
    views = None
    views_match = re.search(r'Views:\s*([\d,]+)', html)
    if views_match:
        views = views_match.group(1)

    # Related Videos
    related_videos = []
    # Related are typically listed below the main content
    for item in soup.select(".post-thumbnail, .item-list .post"):
        try:
            link = item.select_one("a[href]")
            if not link:
                continue
            r_url = link.get("href", "")
            if not r_url or "xxxparodyhd.net" not in r_url:
                continue

            r_title = link.get("title") or _text(link)
            img = item.select_one("img")
            r_thumb = _best_image_url(img)
            r_dur = None
            dur_el = item.select_one(".duration, .runtime")
            if dur_el:
                r_dur = _text(dur_el)

            related_videos.append({
                "url": r_url,
                "title": r_title,
                "thumbnail_url": r_thumb,
                "duration": r_dur,
            })
            if len(related_videos) >= 10:
                break
        except Exception:
            continue

    return {
        "url": url,
        "title": title,
        "description": description,
        "thumbnail_url": thumbnail,
        "tags": tags,
        "categories": categories,
        "studio": studio,
        "cast": cast,
        "year": year,
        "views": views,
        "related_videos": related_videos,
        "video": {
            "default": video_url,
            "has_video": video_url is not None,
            "streams": streams,
        },
    }


async def scrape(url: str) -> dict[str, Any]:
    html = await fetch_html(url)
    return await parse_page(html, url)


def get_categories() -> list[dict[str, Any]]:
    file_path = os.path.join(os.path.dirname(__file__), "categories.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


async def list_videos(base_url: str, page: int = 1, limit: int = 20) -> list[dict[str, Any]]:
    target_url = base_url.rstrip("/")

    if page > 1:
        if "?" in target_url:
            base, query = target_url.split("?", 1)
            target_url = f"{base.rstrip('/')}/page/{page}/?{query}"
        else:
            target_url = f"{target_url}/page/{page}/"
    elif not target_url.endswith("/") and "?" not in target_url:
        target_url += "/"

    import httpx
    try:
        html = await fetch_html(target_url)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return []
        raise

    if not html:
        return []
        
    soup = BeautifulSoup(html, "lxml")

    items: list[dict[str, Any]] = []

    # XXXParodyHD uses .ml-item containers (WP-Movie theme)
    for card in soup.select(".ml-item"):
        try:
            # Main link: a.ml-mask
            link = card.select_one("a.ml-mask")
            if not link:
                link = card.select_one("a[href]")
            if not link:
                continue

            href = link.get("href", "") or link.get("data-href", "")
            if not href:
                continue

            # Skip non-video links
            skip_patterns = ["/category/", "/genre/", "/director/", "/cast/",
                             "/release-year/", "/page/", "#", "/tag/"]
            if any(p in href for p in skip_patterns):
                continue

            # Title from .mli-info h2, or link title/oldtitle attribute
            title_el = card.select_one(".mli-info h2")
            title = _text(title_el) if title_el else (
                link.get("oldtitle") or link.get("title") or _text(link)
            )
            if not title:
                continue

            # Thumbnail
            img = card.select_one("img")
            thumb = _best_image_url(img)

            # Duration from .mli-info1
            dur_el = card.select_one(".mli-info1")
            duration = _text(dur_el) if dur_el else None

            # Year from hidden_tip div
            year = None
            tip = card.select_one("#hidden_tip")
            if tip:
                year_link = tip.select_one("a[href*='/release-year/']")
                if year_link:
                    year = _text(year_link)

            items.append({
                "url": href,
                "title": title or "Unknown Video",
                "thumbnail_url": thumb,
                "duration": duration,
                "upload_time": year,
            })
        except Exception:
            continue

    return items

