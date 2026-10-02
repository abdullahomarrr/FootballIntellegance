import hashlib

import httpx
import respx

from football_intelligence.providers.wyscout_open import (
    ARTICLES_URL,
    COLLECTION_ID,
    COLLECTION_URL,
    WyscoutFile,
    WyscoutOpenAdapter,
)


@respx.mock
def test_catalogue_includes_file_license_and_checksum():
    article_url = "https://api.figshare.com/v2/articles/7765316"
    respx.get(COLLECTION_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": COLLECTION_ID,
                "title": "Soccer match event dataset",
                "doi": "10.6084/m9.figshare.c.4415000.v5",
            },
        )
    )
    respx.get(ARTICLES_URL, params={"page_size": 1000}).mock(
        return_value=httpx.Response(200, json=[{"url_public_api": article_url}])
    )
    respx.get(article_url).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 7765316,
                "title": "Competitions",
                "doi": "10.6084/m9.figshare.7765316.v4",
                "published_date": "2019-05-06T13:02:17Z",
                "license": {
                    "name": "CC BY 4.0",
                    "url": "https://creativecommons.org/licenses/by/4.0/",
                },
                "files": [
                    {
                        "name": "competitions.json",
                        "download_url": "https://ndownloader.figshare.com/files/15073685",
                        "size": 2139,
                        "computed_md5": "a" * 32,
                    }
                ],
            },
        )
    )

    catalogue = WyscoutOpenAdapter().discover_catalogue()

    assert catalogue.title == "Soccer match event dataset"
    assert catalogue.articles[0].license_name == "CC BY 4.0"
    assert catalogue.articles[0].files[0].name == "competitions.json"
    assert catalogue.articles[0].files[0].computed_md5 == "a" * 32


@respx.mock
def test_verified_download_checks_size_and_md5(tmp_path):
    content = b"licensed open data"
    url = "https://example.test/events.zip"
    respx.get(url).mock(return_value=httpx.Response(200, content=content))
    file = WyscoutFile(
        name="events.zip",
        download_url=url,
        size=len(content),
        computed_md5=hashlib.md5(content, usedforsecurity=False).hexdigest(),
    )
    target = tmp_path / "events.zip"
    assert WyscoutOpenAdapter().download_verified(file, target) == target
    assert target.read_bytes() == content
