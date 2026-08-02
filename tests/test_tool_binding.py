from traceable_deep_agents_sample.tool_binding import ToolBindingResolver


def test_tool_binding_resolver_scopes_binding_to_tenant():
    resolver = ToolBindingResolver()

    org_a = resolver.resolve(tenant_id="org:a", tool_name="search_tech_news")
    org_b = resolver.resolve(tenant_id="org:b", tool_name="search_tech_news")

    assert org_a.binding_id == "org:a:technews.read"
    assert org_b.binding_id == "org:b:technews.read"
    assert org_a.credential_ref == "[REDACTED]"
    assert org_a.credential_ref_hash != org_b.credential_ref_hash
    assert org_a.allowed_scopes == ("read:issues",)


def test_tool_binding_resolver_uses_detail_scope_for_article_lookup():
    binding = ToolBindingResolver().resolve(tenant_id="org:a", tool_name="get_tech_news_article")

    assert binding.allowed_scopes == ("read:issue-detail",)
