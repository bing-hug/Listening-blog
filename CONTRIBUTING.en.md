# Contributing to JuFlow

Setting up a local dev environment is in the [README's Development section](README.en.md#development). This file covers writing adapter plugins.

## Writing an adapter plugin

Adapters subclass a base class and mostly just declare configuration. Three bases to choose from:

**RSSHub adapter** (simplest — try this first):

```python
# adapter.py
from app.adapters.rsshub_base import RsshubBaseAdapter

class MyAdapter(RsshubBaseAdapter):
    platform = "myplatform"
    name = "My Platform"
    url_pattern = r"https?://myplatform\.com/user/(\w+)"
    rsshub_route_template = "/myplatform/user/{uid}"
    display_name_template = "User {uid}"
    home_url_template = "https://myplatform.com/user/{uid}"
```

**Direct RSS adapter**:

```python
from app.adapters.rss_base import DirectRssBaseAdapter

class MyAdapter(DirectRssBaseAdapter):
    platform = "myplatform"
    name = "My Platform"
    url_pattern = r"https?://myplatform\.com/blog/(\w+)"
    rss_url_template = "https://myplatform.com/blog/{uid}/rss"
    home_url_template = "https://myplatform.com/blog/{uid}"
```

**Scraper adapter** (`title` and `summary` accept `|`-separated fallbacks — `"a.title|a"` tries `a.title` first, then `a`):

```python
from app.adapters.scraper_base import ScraperBaseAdapter, ScraperSelectors

class MyAdapter(ScraperBaseAdapter):
    platform = "myplatform"
    name = "My Platform"
    url_pattern = r"https?://myplatform\.com/u/(\w+)"
    profile_url_template = "https://myplatform.com/u/{uid}"
    selectors = ScraperSelectors(
        item=".post-item",
        title="a.title|a",
        summary=".summary|p",
        url_prefix="https://myplatform.com",
    )
```

Each plugin also needs a `manifest.json`:

```json
{
  "name": "myplatform",
  "display_name": "My Platform",
  "version": "1.0.0",
  "author": "your-name",
  "description": "My Platform adapter",
  "adapter_class": "MyAdapter"
}
```

