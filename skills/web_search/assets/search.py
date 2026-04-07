"""Web search skill - search the internet for information"""

import urllib.request
import urllib.parse
import json
from typing import List, Dict, Optional


def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for information using DuckDuckGo.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default 5)

    Returns:
        Search results as formatted text
    """
    try:
        # Use DuckDuckGo HTML search (no API key required)
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        # Create request with user agent
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

        # Fetch results
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')

        # Simple extraction of results (in production, use proper HTML parsing)
        results = _extract_results(html, max_results)

        if not results:
            return f"No results found for '{query}'"

        # Format results
        output = [f"Search results for: {query}\n"]
        for i, result in enumerate(results, 1):
            output.append(f"{i}. {result['title']}")
            output.append(f"   URL: {result['url']}")
            output.append(f"   {result['snippet']}")
            output.append("")

        return '\n'.join(output)

    except Exception as e:
        return f"Search error: {type(e).__name__}: {e}"


def _extract_results(html: str, max_results: int) -> List[Dict[str, str]]:
    """Extract search results from DuckDuckGo HTML (simple extraction)"""
    results = []

    # Simple text-based extraction (for production use BeautifulSoup)
    # This is a simplified version
    try:
        # Look for result links and snippets
        lines = html.split('\n')
        current_result = {}

        for line in lines:
            if 'class="result__a"' in line and 'href=' in line:
                # Extract URL and title
                start = line.find('href="') + 6
                end = line.find('"', start)
                if start > 6 and end > start:
                    url = line[start:end]
                    # Extract title from between > and <
                    title_start = line.find('>', end)
                    if title_start > 0:
                        title_end = line.find('<', title_start + 1)
                        if title_end > title_start:
                            title = line[title_start + 1:title_end].strip()
                            current_result = {
                                'url': url,
                                'title': title,
                                'snippet': ''
                            }

            elif 'class="result__snippet"' in line and current_result:
                # Extract snippet
                start = line.find('>') + 1
                end = line.rfind('<')
                if start > 0 and end > start:
                    snippet = line[start:end].strip()
                    current_result['snippet'] = snippet
                    results.append(current_result)
                    current_result = {}

                    if len(results) >= max_results:
                        break
    except Exception:
        pass

    return results


def search_wikipedia(query: str, max_sentences: int = 3) -> str:
    """Search Wikipedia for information.

    Args:
        query: Search query
        max_sentences: Maximum number of sentences in summary

    Returns:
        Wikipedia summary or error message
    """
    try:
        # Use Wikipedia API
        encoded_query = urllib.parse.quote(query)
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"

        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Easy-Agent/1.0'}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        if 'extract' not in data:
            return f"No Wikipedia results found for '{query}'"

        # Limit to max_sentences
        extract = data['extract']
        sentences = extract.split('. ')
        limited = '. '.join(sentences[:max_sentences])
        if len(sentences) > max_sentences:
            limited += '...'

        return f"{data['title']}\n\n{limited}\n\nSource: {data.get('content_urls', {}).get('desktop', {}).get('page', 'N/A')}"

    except Exception as e:
        return f"Wikipedia search error: {type(e).__name__}: {e}"
