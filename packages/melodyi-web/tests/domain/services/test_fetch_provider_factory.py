"""FetchProviderFactory 单元测试

回归保护：抓取供应商名称统一为 `jina`，旧名 `jina-reader` 不再合法。
"""

import pytest
from pydantic import ValidationError

from melodyi_web.domain.models.fetch_provider_config import FetchProviderConfig
from melodyi_web.domain.services.fetch_provider_factory import FetchProviderFactory
from melodyi_web.providers.fetch.jina_reader_provider import JinaReaderProvider
from melodyi_web.providers.fetch.markdown_new_provider import MarkdownNewProvider


class TestFetchProviderFactory:
    """供应商工厂测试"""

    def test_create_jina(self):
        """name=jina 应创建 JinaReaderProvider，且自报名称为 jina"""
        provider = FetchProviderFactory.create(FetchProviderConfig(name="jina"))
        assert isinstance(provider, JinaReaderProvider)
        assert provider.name == "jina"

    def test_create_markdown_new(self):
        """name=markdown-new 应创建 MarkdownNewProvider"""
        provider = FetchProviderFactory.create(FetchProviderConfig(name="markdown-new"))
        assert isinstance(provider, MarkdownNewProvider)

    def test_jina_reader_is_rejected(self):
        """回归测试：jina-reader 不再是合法供应商名

        历史上 SKILL.md/CLI 误用 jina-reader，但 FetchProviderConfig 的
        Literal 不接受该值，导致 `-p jina-reader` 在构造 FetchProviderConfig
        时即抛 ValidationError（工厂里的 legacy 映射根本到不了）。
        统一为 jina 后，该名应被显式拒绝，避免再次回退到双命名。
        """
        with pytest.raises(ValidationError):
            FetchProviderConfig(name="jina-reader")
