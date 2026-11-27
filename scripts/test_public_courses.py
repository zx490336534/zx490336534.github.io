"""Privacy boundary and navigation regressions for the public course export."""
import re
import subprocess
import sys
from pathlib import Path
import unittest
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup
from build_public_courses import COURSES, DEEP, LABS
from course_curriculum import TERMS

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = re.compile(r"""(?ix)
    /Users/|/home/[a-z]+/|https?://(?:localhost|127\.0\.0\.1)\b
    |(?:https?://[^/"'\s]+)?\b(?:qunhequnhe|kujiale|aihom\.ai)\b
    |\b(?:COOAI|HUXING)-\d+|\b(?:Kaptain|Coops|TDDL)\b
    |internal-concepts|src/main/java|\b(?:ai-native-service|auto-layout-service|kuai-service-(?:py|front))\b
    |\b(?:password|secret|api[_-]?key|access[_-]?token)\s*[:=]
    |\b(?:BEGIN [A-Z ]*PRIVATE KEY|AKIA[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{30,})\b
""")
ALLOWED_EXTERNAL_HOSTS = {"www.zhongxin.website", "github.com"}


class PublicCoursesTest(unittest.TestCase):
    def test_public_export_inventory_and_links(self):
        for slug, _, _, _, lessons in COURSES:
            with self.subTest(course=slug):
                expected = {"lessons/index.html", *(f"lessons/{item[0]}.html" for item in lessons)}
                files = {p.relative_to(ROOT / slug).as_posix() for p in (ROOT / slug).rglob("*") if p.is_file()}
                self.assertEqual(files, expected | {f"examples/{LABS[slug][0]}"}, "Course roots should contain only the public export")
                self.assertEqual(set(TERMS[slug]), {lesson[0] for lesson in lessons})
                self.assertEqual(set(DEEP[slug]), {lesson[0] for lesson in lessons})
                for path in expected:
                    f = ROOT / slug / path
                    raw = f.read_text(encoding="utf-8")
                    decoded = unquote(raw)
                    self.assertIsNone(FORBIDDEN.search(decoded), f"Sensitive pattern in {slug}/{path}")
                    soup = BeautifulSoup(raw, "html.parser")
                    self.assertEqual(len(soup.find_all("h1")), 1)
                    self.assertEqual(soup.select_one(".masthead nav [aria-current]")["href"], "/lab/")
                    self.assertEqual(soup.select_one('link[rel="canonical"]')["href"], f"https://www.zhongxin.website/{slug}/{path}")
                    self.assertEqual(len(soup.select('script[id="site-analytics"]')), 1)
                    self.assertTrue(soup.select_one(".public-course"))
                    self.assertNotRegex(soup.get_text(), r"无需账号|公司环境|无需访问公司|真实账号")
                    if path != "lessons/index.html":
                        self.assertGreaterEqual(len(soup.select(".course-flow li")), 3)
                        self.assertGreaterEqual(len(soup.select(".code-notes > div")), 3)
                        self.assertGreaterEqual(len(soup.select(".failure-card")), 2)
                        self.assertGreaterEqual(len(soup.select(".course-assertions li")), 3)
                        self.assertGreaterEqual(len(soup.select_one("#code-walkthrough pre code").get_text().splitlines()), 15)
                    for node in soup.select("[href], [src]"):
                        link = urlsplit(node.get("href") or node.get("src"))
                        if link.scheme == "mailto":
                            self.assertEqual(link.path, "490336534@qq.com")
                            continue
                        if link.netloc:
                            self.assertIn(link.netloc, ALLOWED_EXTERNAL_HOSTS)
                        elif link.path:
                            target = (ROOT if link.path.startswith("/") else f.parent) / unquote(link.path.lstrip("/"))
                            if target.is_dir():
                                target /= "index.html"
                            self.assertTrue(target.is_file(), f"{f.name} refers to missing {link.path}")
                        elif link.fragment:
                            self.assertIsNotNone(soup.find(id=link.fragment), f"Missing anchor in {f.name}")

    def test_public_sources_are_clean(self):
        for rel in ("scripts/course_curriculum.py", "scripts/course_code_walkthroughs.py", "scripts/build_public_courses.py", "js/public-courses.js"):
            self.assertIsNone(FORBIDDEN.search((ROOT / rel).read_text(encoding="utf-8")), rel)

    def test_reference_projects(self):
        for slug, (filename, _, expected) in LABS.items():
            with self.subTest(course=slug):
                script = ROOT / slug / "examples" / filename
                self.assertIsNone(FORBIDDEN.search(script.read_text(encoding="utf-8")), filename)
                output = subprocess.check_output([sys.executable, str(script)], text=True, timeout=10)
                self.assertIn(expected, output)
