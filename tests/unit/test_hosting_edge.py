# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for the hosting_edge filters (plugins/filter/hosting_edge.py).

Each gate the filters implement has a fixture that must FAIL (the gate fires) and a near-miss that
must PASS (the gate does not fire on something that only looks similar).

Run from the collection root: `python -m pytest tests/unit/test_hosting_edge.py -q` (it imports the
filter module by path, two levels up), or `ansible-test units` in an ansible_collections/ checkout.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "plugins", "filter"))

import hosting_edge as he  # noqa: E402

WILD = ["*.dev.example.com", "*.apps.example.com"]
APPS = [
    {
        "name": "zone-wide",
        "domain": "*.example.com",
        "self_hosted_domains": ["*.example.com"],
    },
    {"name": "api", "domain": "api.example.com"},
    {"name": "tool-path", "domain": "tool.example.com/mcp"},
    {
        "name": "dashboards",
        "domain": "grafana.example.com",
        "self_hosted_domains": ["grafana.example.com", "metrics.example.com"],
    },
]
NEW = [
    {"name": "hosting-dev", "domain": "*.dev.example.com"},
    {"name": "hosting-prod", "domain": "*.apps.example.com"},
]
INGRESS = [
    {"hostname": "api.example.com", "service": "http://origin.example.com:8080"},
    {"hostname": "grafana.example.com", "service": "https://proxy.example.com:443"},
    {"service": "http_status:404"},
]
DEV_RULE = {
    "hostname": "*.dev.example.com",
    "service": "http://hosting.example.com:8080",
}


# ------------------------------------------------------------------------------------ matches
@pytest.mark.parametrize(
    "pattern,host",
    [
        ("*.dev.example.com", "a.dev.example.com"),
        ("*.dev.example.com", "a.b.dev.example.com"),
        ("*.dev.example.com", "A.DEV.Example.com"),
        ("api.example.com", "api.example.com"),
        ("tool.example.com/mcp", "tool.example.com"),
    ],
)
def test_matches(pattern, host):
    assert he.hosting_edge_matches(pattern, host)


@pytest.mark.parametrize(
    "pattern,host",
    [
        ("*.dev.example.com", "dev.example.com"),  # the wildcard's own apex
        ("*.dev.example.com", "xdev.example.com"),  # suffix lookalike
        ("*.dev.example.com", "dev.example.com.evil.test"),
        (
            "api.example.com",
            "x.api.example.com",
        ),  # an exact name covers nothing below it
    ],
)
def test_matches_near_misses(pattern, host):
    assert not he.hosting_edge_matches(pattern, host)


# ------------------------------------------------------------------------------------ captured
def test_captured_fires_at_any_depth():
    hosts = ["foo.dev.example.com", "x.y.apps.example.com", "api.example.com"]
    assert he.hosting_edge_captured(WILD, hosts) == [
        "foo.dev.example.com",
        "x.y.apps.example.com",
    ]


def test_captured_near_misses():
    hosts = [
        "dev.example.com",
        "xdev.example.com",
        "*.example.com",
        "*.dev.example.com",
    ]
    assert he.hosting_edge_captured(WILD, hosts) == []


# ------------------------------------------------------------------------------------ winner
def test_winner_specificity():
    apps = APPS + NEW
    assert he.hosting_edge_winner(apps, "hello.dev.example.com") == "hosting-dev"
    assert he.hosting_edge_winner(apps, "a.b.dev.example.com") == "hosting-dev"
    assert he.hosting_edge_winner(apps, "api.example.com") == "api"
    assert he.hosting_edge_winner(apps, "metrics.example.com") == "dashboards"
    assert he.hosting_edge_winner(apps, "dev.example.com") == "zone-wide"
    # a path app decides only its path, never the root
    assert he.hosting_edge_winner(apps, "tool.example.com") == "zone-wide"
    assert he.hosting_edge_winner([], "api.example.com") is None


def test_winner_map():
    assert he.hosting_edge_winner_map(
        APPS, ["api.example.com", "api.example.com", "x.example.com"]
    ) == {
        "api.example.com": "api",
        "x.example.com": "zone-wide",
    }


def test_winner_diff_fires():
    changed = APPS + [{"name": "oops", "domain": "other.example.com"}]
    assert he.hosting_edge_winner_diff(APPS, changed, ["api.example.com", "other.example.com"]) == [
        "other.example.com"
    ]


def test_winner_diff_near_miss():
    assert he.hosting_edge_winner_diff(APPS, APPS + NEW, ["api.example.com", "x.example.com"]) == []


# ------------------------------------------------------------------------------------ existing hosts
def test_existing_hosts():
    dns = [{"name": "API.example.com"}, {"name": "*.example.com"}]
    out = he.hosting_edge_existing_hosts(dns, ["grafana.example.com"], APPS + NEW, ["hosting-dev"])
    assert "api.example.com" in out
    assert "tool.example.com" in out  # path stripped
    assert "metrics.example.com" in out
    assert not any(h.startswith("*.") for h in out)  # patterns are rules, not names
    assert out == sorted(set(out))


# ------------------------------------------------------------------------------------ merge
def test_merge_adds_before_catch_all_and_is_idempotent():
    after = he.hosting_edge_merge_ingress(INGRESS, [DEV_RULE])
    assert after[-1] == {"service": "http_status:404"}
    assert after[-2] == DEV_RULE
    assert all(r in after for r in INGRESS)
    assert he.hosting_edge_merge_ingress(after, [DEV_RULE]) == after


@pytest.mark.parametrize(
    "before,wanted,reason",
    [
        (INGRESS[:-1], [DEV_RULE], "catch-all"),
        (INGRESS + [{"service": "http_status:404"}], [DEV_RULE], "catch-all"),
        (
            INGRESS,
            [{"hostname": "api.example.com", "service": "http://evil.test"}],
            "wildcard",
        ),
    ],
)
def test_merge_refuses(before, wanted, reason):
    with pytest.raises(he.AnsibleFilterError, match=reason):
        he.hosting_edge_merge_ingress(before, wanted)


# ------------------------------------------------------------------------------------ certificates
def test_cert_missing():
    universal = [{"status": "active", "hosts": ["example.com", "*.example.com"]}]
    pending = [{"status": "pending_validation", "hosts": WILD}]
    active = [{"status": "active", "hosts": ["*.DEV.example.com", "*.Apps.example.com"]}]
    half = [{"status": "active", "hosts": ["*.dev.example.com"]}]
    assert he.hosting_edge_cert_missing(universal, WILD) == WILD
    assert he.hosting_edge_cert_missing(pending, WILD) == WILD
    assert he.hosting_edge_cert_missing(active, WILD) == []
    assert he.hosting_edge_cert_missing(half, WILD) == ["*.apps.example.com"]
    assert he.hosting_edge_cert_missing(None, WILD) == WILD


def test_filter_module_exports_every_function():
    names = set(he.FilterModule().filters())
    assert names == {n for n in dir(he) if n.startswith("hosting_edge_")}
