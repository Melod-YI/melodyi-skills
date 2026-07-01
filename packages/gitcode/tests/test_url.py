"""parse_pr_url 单元测试"""

import pytest

from gitcode.url import PRRef, RepoRef, parse_pr_url, parse_repo_url, UrlParseError


@pytest.mark.parametrize("url,expected", [
    ("https://gitcode.net/owner/repo/-/merge_requests/123",
     PRRef("owner", "repo", "123")),
    ("https://gitcode.com/owner/repo/pulls/456",
     PRRef("owner", "repo", "456")),
    ("https://gitcode.com/owner/repo/-/merge_requests/789",
     PRRef("owner", "repo", "789")),
    ("https://gitcode.com/owner/repo/-/merge_requests/789/diffs",
     PRRef("owner", "repo", "789")),
    ("https://gitcode.com/owner/repo/merge_requests/789",
     PRRef("owner", "repo", "789")),
    ("http://gitcode.com/Owner/Repo.Name/-/merge_requests/1",
     PRRef("Owner", "Repo.Name", "1")),
])
def test_parse_pr_url_valid(url, expected):
    assert parse_pr_url(url) == expected


@pytest.mark.parametrize("url", [
    "not a url",
    "https://gitcode.com/owner/repo",
    "https://gitcode.com/owner/repo/issues/1",
    "https://example.com/owner/repo/pulls/1",
])
def test_parse_pr_url_invalid(url):
    with pytest.raises(UrlParseError):
        parse_pr_url(url)


@pytest.mark.parametrize("url,expected", [
    ("https://gitcode.com/openJiuwen/jiuwenswarm",
     RepoRef("openJiuwen", "jiuwenswarm")),
    ("https://gitcode.com/openJiuwen/jiuwenswarm/",
     RepoRef("openJiuwen", "jiuwenswarm")),
    ("https://gitcode.com/openJiuwen/jiuwenswarm/-/merge_requests/123",
     RepoRef("openJiuwen", "jiuwenswarm")),
    ("https://gitcode.com/openJiuwen/jiuwenswarm/pulls/123/diffs",
     RepoRef("openJiuwen", "jiuwenswarm")),
    ("https://gitcode.net/Owner/Repo.Name",
     RepoRef("Owner", "Repo.Name")),
    ("https://gitcode.com/openJiuwen/jiuwenswarm.git",
     RepoRef("openJiuwen", "jiuwenswarm")),
])
def test_parse_repo_url_valid(url, expected):
    assert parse_repo_url(url) == expected


@pytest.mark.parametrize("url", [
    "not a url",
    "https://gitcode.com/owner",
    "https://gitcode.com/",
    "https://example.com/owner/repo",
])
def test_parse_repo_url_invalid(url):
    with pytest.raises(UrlParseError):
        parse_repo_url(url)
