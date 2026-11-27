import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from build_blog import Post, import_posts


class ImportPostsTest(unittest.TestCase):
    route = "/article/example.html"
    base = "https://mp.weixin.qq.com/s"

    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.input = Path(directory.name) / "posts.json"

    def item(self, **changes):
        return {"path": self.route, "title": "原稿", "published": "2026-11-27",
                "source": self.base + "/First", "body": "<p>新正文</p>", **changes}

    def previous(self, source):
        return Post(self.route, "原稿", "2026-11-27T09:00:00+08:00", '<p id="old">旧正文</p>',
                    "摘要", source=source)

    def run_import(self, items, previous=()):
        self.input.write_text(json.dumps(items, ensure_ascii=False))
        return import_posts(self.input, previous)

    def test_duplicate_route_fails_even_if_sources_match(self):
        for suffix in ("/First", "/Second"):
            with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, "重复文章地址"):
                self.run_import([self.item(), self.item(source=self.base + suffix)])

    def test_summary_line_breaks_and_literal_code_escapes(self):
        for body, raw, expected in [
            ("<p>甲</p><p>乙</p>", r"甲\x0d\x0a乙", "甲 乙"),
            (r"<code>\x0a</code>", r"换行符 \x0a", r"换行符 \x0a"),
        ]:
            with self.subTest(raw=raw):
                [post] = self.run_import([self.item(body=body, description=raw)])
                self.assertEqual(post.description, expected)

    def test_known_source_allows_reimport_and_preserves_metadata_and_anchors(self):
        for old, new in [
            ("/First", "/First?scene=1#wechat_redirect"),
            ("?__biz=A&mid=10&idx=2&sn=abc", "?itemidx=2&appmsgid=10&scene=1&__biz=A"),
            ("?signature=signed-link", "?signature=signed-link#wechat_redirect"),
        ]:
            with self.subTest(old=old):
                previous = self.previous(self.base + old)
                [updated] = self.run_import([self.item(source=self.base + new, title="导入稿",
                                                      published="2026-11-26")], [previous])
                self.assertEqual((updated.title, updated.published), (previous.title, previous.published))
                self.assertIn("新正文", updated.body)
                self.assertIn('id="old"', updated.body)

    def test_different_or_unverifiable_sources_cannot_replace_an_article(self):
        for old, new in [
            ("/First", "/Other"),
            ("?__biz=A&mid=10&idx=1", "?__biz=A&mid=10&idx=2"),
            ("?__biz=A&mid=10&idx=1", "?__biz=B&mid=10&idx=1"),
            ("?__biz=A&mid=10&idx=1", "?__biz=A&mid=11&idx=1"),
            ("/First", "?__biz=A&mid=10&idx=1"),
            ("?signature=first", "?signature=other"),
        ]:
            with self.subTest(old=old, new=new), self.assertRaisesRegex(ValueError, "核对原文地址"):
                self.run_import([self.item(source=self.base + new)], [self.previous(self.base + old)])

    def test_first_association_requires_matching_title_and_publication_day(self):
        previous = self.previous("")
        [updated] = self.run_import([self.item()], [previous])
        self.assertEqual(updated.source, self.base + "/First")
        for changes in ({"title": "另一篇"}, {"published": "2026-11-26"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "首次关联"):
                self.run_import([self.item(**changes)], [previous])
